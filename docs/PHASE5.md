# Phase 5 — Duplicate resolution & review tooling

**Status: complete (5a — May 2026)**

**Prerequisite:** Phase 4 complete — [PHASE4.md](./PHASE4.md) (tagging & renaming).

---

## Goal

When automatic duplicate preference (Phase 3) picks the wrong copy, let the DJ **manually choose which file to keep**, archive or demote the rest, and optionally **re-run tagging and routing** for the chosen copy—without auto-deleting files or writing into the watch folder.

This phase answers: *“I have two versions of the same track—why did the pipeline keep the 128k MP3 instead of my FLAC?”*

---

## Current system (handoff from Phase 4)

### Pipeline today

```text
INGEST → ANALYZE → FINGERPRINT → TAG → ROUTE
                      ↓
              duplicates/<hash>/     (non-preferred copies, status duplicate)
              ready/ or review/      (auto-preferred copy after TAG + ROUTE)
```

### What already exists

| Area | Notes |
|------|--------|
| `GET /duplicates` | Lists groups with 2+ members (format, bitrate, status) |
| `POST /duplicates/resolve` | Manual keep + archive; persists `preferred_track_id` |
| `DuplicateGroupsCard.vue` | Keep + archive dialog on dashboard |
| `duplicate_groups` + `fingerprints` tables | Grouping by fingerprint hash |
| `version_priority.py` | Auto-preferred track IDs per format family |
| `archive_folder` | Path in settings; **no automated archive job yet** |

### Frontend patterns (reuse)

- Pinia stores, snackbars, WebSocket pipeline refresh — same as Phases 1–4
- Extend duplicate card with actions and confirmation dialogs

---

## What was delivered (Phase 5a)

### Backend

| Area | Location |
|------|----------|
| Resolve orchestration | `backend/app/services/duplicate_resolve_service.py` |
| API | `backend/app/api/duplicates.py` |
| Schemas | `backend/app/schemas/duplicate.py` |
| Migration | `duplicate_groups.preferred_track_id`, `resolved_at` |
| Manual preference on ingest | `fingerprint_service._after_fingerprint` |

### Frontend

| Feature | Location |
|---------|----------|
| Keep + confirm dialog | `DuplicateGroupsCard.vue` |
| API client | `frontend/src/services/duplicateService.ts` |
| Types | `frontend/src/types/duplicate.ts` |

### Tests

**Backend (60):** `test_duplicate_resolve_service.py`, `test_duplicates_api.py`

```bash
make test
make lint
```

---

## Suggested scope

### Phase 5a — Core (ship first)

#### `POST /duplicates/resolve`

Implement manual resolution with a clear contract:

**Request body (draft):**

```json
{
  "group_id": 1,
  "keep_track_id": 42,
  "archive_track_ids": [43, 44]
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `group_id` | yes | `duplicate_groups.id` |
| `keep_track_id` | yes | Member to treat as preferred going forward |
| `archive_track_ids` | no | Other members to move to `archive/` (default: all non-kept in group) |

**Response:**

```json
{
  "status": "ok",
  "kept_track_id": 42,
  "archived_track_ids": [43]
}
```

**Server behavior (draft):**

1. Validate `keep_track_id` belongs to `group_id`.
2. Persist manual override (e.g. `duplicate_groups.preferred_track_id` or `tracks.user_preferred` flag) so a later ingest does not silently undo the choice without re-resolution.
3. **Keeper:**
   - If file is under `duplicates/<hash>/` or still in `processing/`, ensure a working copy exists in `processing/` (move/copy as needed).
   - Clear `TrackStatus.DUPLICATE` on keeper; set status appropriate for pipeline stage (`ingested` if analysis done, etc.).
   - Enqueue `TAG` then `ROUTE` if not already in `ready/` with a final path (respect existing queue dedup).
4. **Archived members:**
   - Copy or move file to `archive/<fingerprint_hash>/` (mirror duplicates layout).
   - Set `TrackStatus.ARCHIVED` (or keep `DUPLICATE` + `final_path` under archive—pick one convention and document it).
   - Do **not** delete files from disk in v1.
5. **Non-kept, non-archived** (if `archive_track_ids` omitted): leave in `duplicates/<hash>/` with `DUPLICATE` status.
6. Call `notify_pipeline_changed` so dashboard refreshes.

**Errors:** `404` unknown group/track, `409` invalid state (e.g. keeper already archived), `422` validation.

| Area | Location (planned) |
|------|---------------------|
| Resolve orchestration | `backend/app/services/duplicate_resolve_service.py` |
| API | `backend/app/api/duplicates.py` |
| Schemas | `backend/app/schemas/duplicate.py` |
| Migration | `duplicate_groups.preferred_track_id`, optional `resolved_at` |

#### Frontend — duplicate actions (MVP)

| Feature | Location (planned) |
|---------|---------------------|
| Keep / Archive actions per member | `DuplicateGroupsCard.vue` or `DuplicateGroupPanel.vue` |
| Confirm dialog | Vuetify `v-dialog` |
| API client | `frontend/src/services/duplicateService.ts` |
| Types | `frontend/src/types/duplicate.ts` |

**UI flow:**

1. User expands a duplicate group.
2. Table shows: file, format, bitrate, LUFS (if analyzed), artist/title, status, path basename.
3. **Keep** on one row → confirm → `POST /duplicates/resolve` → snackbar + refresh.
4. Optional: **Archive all others** checkbox (default on).

#### Tests

- `test_duplicate_resolve_service.py` — file moves mocked, status transitions, enqueue TAG/ROUTE
- API test for resolve happy path and validation errors
- `duplicateService.test.ts` — resolve client

---

### Phase 5b — Compare UX (optional same milestone)

| Feature | Notes |
|---------|--------|
| Side-by-side metadata | BPM, key, LUFS, duration, tag confidence |
| Waveform preview | Stretch goal — e.g. `GET /tracks/:id/waveform` (ffmpeg peaks PNG or JSON); embed in compare panel |
| Audio A/B | Out of scope for v1 (no in-browser player required by spec) |

Spec reference: [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md) — Duplicate Resolution UI (compare, waveform previews, manual keep/remove).

---

### Phase 5c — Ops polish (can follow 5a)

| Feature | Notes |
|---------|--------|
| `POST /queue/tag-backlog` | Enqueue `TAG` for tracks with `tagged_at IS NULL` still in `processing/` |
| Scheduler retries | `scheduler.py` re-enqueues `FAILED` jobs with backoff (cap attempts) |
| Failed job visibility | Jobs table already exists; surface retry count in UI |

---

### Phase 5d — Settings polish (can follow 5a)

| Feature | Notes |
|---------|--------|
| Loudness thresholds in Settings | `DJ_REVIEW_LUFS_THRESHOLD`, `DJ_REVIEW_TRUE_PEAK_DB` — env today, UI deferred since Phase 2 |
| Duplicate rule toggle | Spec: “FLAC + MP3 keep both by default” — later user-configurable |

---

## File move rules

**Never write inside the watch folder.**

| Source | After “Keep” | After “Archive” |
|--------|----------------|-----------------|
| `duplicates/<hash>/file.ext` | Copy/move to `processing/` for keeper; enqueue pipeline | Move/copy to `archive/<hash>/file.ext` |
| `processing/` (auto-preferred) | Re-tag/route if needed | → `archive/` |
| `ready/` or `review/` (wrong keeper) | Demote: copy to `duplicates/` or `archive/`; promote new keeper through TAG → ROUTE | → `archive/` |

Keep `source_path` immutable as audit trail (Phase 1 principle). Update `processing_path` / `final_path` after moves.

---

## Relationship to earlier phases

| Phase | Duplicate behavior |
|-------|---------------------|
| **3** | Auto-preference only; non-preferred → `duplicates/` |
| **4** | Tag/rename applies to auto-preferred copy only |
| **5** | User override; keeper can be promoted from `duplicates/`; others archived |

Auto rules in `version_priority.py` remain the **default** until the user resolves a group.

---

## Sub-phases (recommended delivery order)

```text
5a  POST /duplicates/resolve + dashboard Keep/Archive     ← minimum shippable
5b  Compare panel + waveform endpoint (optional)
5c  tag-backlog + scheduler retries
5d  loudness + duplicate settings in UI
```

---

## Out of scope (Phase 6+)

- Auto-delete duplicates
- Beatgrid / hot cues / Rekordbox analysis replacement
- Picard CLI orchestration or artwork embed (Phase 4 deferred)
- Essentia in Docker on ARM/Pi
- Full `GET /logs` implementation
- Dashboard CPU/RAM metrics (spec dashboard)
- Smart playlists / AI recommendations

---

## Exit criteria (Phase 5a)

- [x] `POST /duplicates/resolve` implemented (not stub)
- [x] User can keep one member of a group; others archived or left in `duplicates/`
- [x] Keeper can reach `ready/` with Phase 4 renamed filename after resolve
- [x] Manual preference persisted (re-ingest does not override without new resolve)
- [x] `pytest` green; new resolve tests
- [x] `npm test` + `make lint` green
- [x] Dashboard duplicate card supports Keep (+ optional Archive others)
- [x] Docs updated: PHASE5 complete (or 5a complete), ROADMAP

---

## Operational notes

### Try duplicate resolution

1. Drop two copies of the same track (e.g. 128k and 320k MP3, or FLAC + MP3) into `data/watch/`.
2. Wait for fingerprint; one copy → `ready/` or `review/`, other → `data/duplicates/<hash>/`.
3. Dashboard → **Duplicate groups** → **Keep** on the copy you want.
4. Confirm keeper appears under `data/ready/` (after TAG + ROUTE) and others under `data/archive/` or `duplicates/`.

Restart **API**, **worker**, and **frontend** after code changes.

---

## References

- Product spec: [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md) — Duplicate Resolution UI, `POST /duplicates/resolve`
- Roadmap: [ROADMAP.md](./ROADMAP.md)
- Phase 3: [PHASE3.md](./PHASE3.md)
- Phase 4: [PHASE4.md](./PHASE4.md)
