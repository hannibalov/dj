# Phase 4 — Metadata tagging & renaming

**Status: complete** (May 2026)

**Prerequisite:** Phase 3 — [PHASE3.md](./PHASE3.md) (fingerprints & duplicates). **Next:** [PHASE5.md](./PHASE5.md) (duplicate resolution).

---

## Goal

Enrich track metadata via AcoustID (and embedded tags / filename / **MusicBrainz text search** fallback), **rename files** to a consistent DJ library convention, write tags (artist, title, album, genre), resolve **genre / subgenre** (MusicBrainz + embedded tags), then route clean copies to `ready/` for Rekordbox import.

This is the phase that answers: *“Why is my file still named `Wonderwall - Oasis.mp3` in `ready/`?”* — **renaming happens here, not in Phase 2 or 3.**

---

## What was delivered

### Pipeline chain

```text
INGEST → ANALYZE → FINGERPRINT → TAG → ROUTE
                      ↓
              duplicates/<hash>/  (non-preferred copies)
              ready/ or review/   (preferred copy, loudness + metadata rules)
```

- `FingerprintService` enqueues `TAG` (not `ROUTE`) for preferred copies
- `TagService` matches metadata, renames in `processing/`, writes tags, enqueues `ROUTE`
- `RoutingService` copies the **renamed** basename to `ready/` or `review/`

### Backend — metadata

| Area | Location |
|------|----------|
| Filename sanitizer & template | `backend/app/metadata/rename.py` |
| Embedded / filename hints | `backend/app/metadata/tags.py` |
| AcoustID lookup | `backend/app/metadata/acoustid_lookup.py` |
| MusicBrainz genre/tags | `backend/app/metadata/musicbrainz_lookup.py` |
| Genre resolve (MB + embedded) | `backend/app/metadata/genre_resolve.py` |
| Genre backfill (API) | `backend/app/services/genre_backfill_service.py` |
| Match orchestration | `backend/app/metadata/matcher.py` |
| Pipeline step (API) | `backend/app/utils/pipeline_stage.py` |
| Job handler | `backend/app/services/tag_service.py` |
| Manual metadata override | `backend/app/services/track_metadata_service.py` |
| Review approve + genre backfill | `backend/app/services/track_lifecycle_service.py` |
| WAV/AIFF ID3 tag I/O | `backend/app/metadata/tags.py` (`TCON`, `TPE1`, `TIT2`, …) |

**API field added:** `pipeline_stage` on each track (derived; not a DB column) — granular in-progress step for the dashboard.

**Track columns added:** `album`, `mix_version`, `musicbrainz_recording_id`, `tag_confidence`, `needs_metadata_review`, `tagged_at`, `genre`, `subgenre`

**Fingerprint column added:** `raw_fingerprint` (Chromaprint string for AcoustID)

**Config / settings:** `DJ_ACOUSTID_API_KEY`, `DJ_TAG_CONFIDENCE_THRESHOLD`, `DJ_NAMING_TEMPLATE` (UI-overridable in Settings)

### Renaming convention

```text
Title - Artist (Mix).ext
```

Default template: `{title} - {artist} ({mix}){ext}` — missing mix becomes `Original Mix`.

ID3 tags still store `artist` and `title` fields separately; only the **filename** uses song name first.

### Routing (refined)

- **Loudness gate:** integrated LUFS below threshold, or true peak above threshold (default `3.0` dBTP — see [README § Configuration](../README.md#configuration))
- **Quality gate:** MP3 below min bitrate, or lossless below min bit depth / sample rate (defaults: 320 kbps, 16-bit, 44.1 kHz; set `0` in Settings to disable a check)
- Low-confidence metadata → `needs_metadata_review` → `review/` even when loudness and quality are OK
- No match still enqueues `ROUTE` (original basename, metadata review flag)

### Frontend (dashboard tracks table)

| Feature | Location |
|---------|----------|
| Artist / title / genre / subgenre (editable → `PATCH /tracks/{id}/metadata`; artist/title rename file per naming template) | `TracksTable.vue`, `trackService.ts` |
| **Pipeline step chips** (awaiting analyze, analyzed, awaiting tag, …) | `QueueStatsCard.vue`, `utils/pipelineStage.ts` |
| Format / quality / bitrate (from file via API; sortable columns) | `TracksTable.vue`, `utils/audioQuality.ts` |
| Loudness badges (OK / Too quiet / High peak; thresholds from Settings) | `TracksTable.vue`, `utils/loudness.ts` |
| Metadata review chip | `TracksTable.vue` |
| Tagging settings | `TagSettingsForm.vue`, `SettingsPage.vue` |
| Loudness + quality gate settings | `LoudnessSettingsForm.vue`, `QualitySettingsForm.vue`, `SettingsPage.vue` |

### Metadata matching (TAG step)

Priority order for **artist / title**:

1. **AcoustID** fingerprint lookup (requires `DJ_ACOUSTID_API_KEY` + Chromaprint fingerprint).
2. **Embedded tags** (ID3/Vorbis), with YouTube-style junk normalized (`backend/app/metadata/normalize.py`).
3. **Filename** from the watch-folder drop or processing basename (`Title - Artist` or `Artist - Title`).
4. **MusicBrainz disambiguation** — when the filename has `Artist - Title` or `Title - Artist`, queries MusicBrainz with **both** orderings and picks the best match (duration + segment alignment). Canonical artist/title from MusicBrainz; source: `musicbrainz`. Beats filename heuristics and unverified embedded tags.

Low-confidence or no match sets `needs_metadata_review` and routes to `review/` even when loudness/quality are OK.

### Genre / subgenre (TAG step)

Genre does **not** require AcoustID. Sources (in order):

1. **MusicBrainz recording** — genres + community tags (`GET /recording/{id}?inc=genres+tags`).
2. **MusicBrainz release** — if the recording has no tags, top linked **release** genres/tags (up to 3 releases).
3. **MusicBrainz artist** — if still empty, primary **artist** genres/tags (up to 2 artists).
4. **Embedded** `genre` tag in the file (`Genre; Subgenre` split when compound).

Recording ID comes from AcoustID, or **artist/title search** (same query as metadata fallback).

On **Approve** (`POST /tracks/{id}/confirm-review`), missing genre/subgenre is fetched again from MusicBrainz and written to the file before moving to `ready/`.

On **manual metadata edit** (`PATCH /tracks/{id}/metadata`), genre/subgenre are written to the file when changed; if only artist/title changed and genre/subgenre are still missing, they are re-fetched from MusicBrainz.

**Genre backfill** (`POST /queue/genre-backfill` or dashboard **Genre backfill**) re-runs MusicBrainz lookup for all tracks that already have artist + title but are missing genre or subgenre — without a full reanalyze. Runs inline in the API (respects MB 1 req/s; can take several minutes on large libraries).

For a **full metadata refresh** (artist, title, rename, route gates), use **Reanalyze all** instead.

MusicBrainz requests are throttled to 1 req/s; fine with a single worker or inline backfill.

Implementation:

| Area | Location |
|------|----------|
| MB recording search | `backend/app/metadata/musicbrainz_lookup.py` (`search_recording_match`) |
| MB release + artist fallback | `backend/app/metadata/musicbrainz_lookup.py` (`lookup_recording_genres`) |
| Genre resolve | `backend/app/metadata/genre_resolve.py` |
| Genre backfill (API) | `backend/app/services/genre_backfill_service.py` |
| Matcher + MB fallback | `backend/app/metadata/matcher.py` |
| Manual edit genre re-resolve | `backend/app/services/track_metadata_service.py` |

Details:

1. **Genre** — top MusicBrainz genre, else top tag, else embedded `genre` tag (at each MB entity level: recording → release → artist).
2. **Subgenre** — more specific MusicBrainz tag (e.g. `Techno` → `Minimal Techno`), else second part of embedded `Genre; Subgenre`.
3. Written to DB and to the file genre tag as `Genre; Subgenre` when both exist.

### WAV / AIFF tagging

Lossless files use **ID3 frames** inside the WAV/AIFF container (`TPE1`, `TIT2`, `TCON`), not mutagen’s “easy” API. Assigning plain strings caused `not a Frame instance` TAG failures on `.wav` in older builds.

### Tests

**Backend (36):** `test_rename`, `test_tag_service`, updated fingerprint tests.

```bash
make test
make lint
```

---

## Track & job lifecycle (Phase 4)

| Job types used | `ingest`, `analyze`, `fingerprint`, `tag`, `route` |

### Dashboard pipeline steps (`pipeline_stage`)

Terminal statuses mirror `TrackStatus`. While `status` is `ingested`, the API exposes the **next worker step**:

| `pipeline_stage` | UI label | Meaning |
|------------------|----------|---------|
| `queued` | Queued | Waiting for ingest |
| `ingesting` | Ingesting | Copying into `processing/` |
| `awaiting_analyze` | Awaiting analyze | Ingested; LUFS/BPM not done yet |
| `awaiting_fingerprint` | Analyzed | Analyze done; fingerprint job next |
| `awaiting_tag` | Awaiting tag | Fingerprint done (or reused); tag job next |
| `awaiting_route` | Awaiting route | Tagged; route job next |
| `ready` / `review` / `duplicate` / `failed` / `archived` | (same) | Terminal |

`track_summary.by_pipeline_stage` drives the dashboard chips (full DB counts, not limited to the tracks table).

| Track field | Meaning |
|-------------|---------|
| `genre` / `subgenre` | Set at TAG (MusicBrainz recording → release → artist + embedded); editable in dashboard; backfill on **Approve**, **Genre backfill**, or manual metadata edit |
| `musicbrainz_recording_id` | From AcoustID or MusicBrainz artist/title search |
| `needs_metadata_review` | Tag confidence below threshold or no match |
| `tagged_at` | Tag job completed (idempotent skip) |

---

## API (metadata & review)

| Method | Path | Purpose |
|--------|------|---------|
| PATCH | `/tracks/{id}/metadata` | Body: `{ "artist", "title", "genre?", "subgenre?" }` — write tags, rename file, set `tagged_at`; write genre/subgenre when changed; re-fetch missing genre/subgenre when only artist/title changed |
| POST | `/tracks/{id}/confirm-review` | Approve `review/` → `ready/`; MusicBrainz genre backfill if missing |
| POST | `/queue/genre-backfill` | Re-fetch missing genre/subgenre for tagged tracks (inline MB lookup) |

---

## Operational notes

### AcoustID API key (recommended)

1. Register at https://acoustid.org/new-application
2. Set `DJ_ACOUSTID_API_KEY` in `.env`

**Without a key:** tagging uses embedded tags, filename parsing, and **MusicBrainz text search** (artist/title from filename) for genre and for low-confidence metadata upgrades.

**With a key:** AcoustID fingerprint match is preferred; MusicBrainz recording ID and genres follow from the match when score is high enough.

Worker needs outbound HTTPS to `api.acoustid.org` and `musicbrainz.org`.

### Try renaming

1. Drop `Wonderwall - Oasis.mp3` into `data/watch/` (basename may be title–artist or artist–title).
2. Let the pipeline run through `TAG`.
3. Check `data/processing/` then `data/ready/` — file should be `Wonderwall - Oasis (Original Mix).mp3` (when metadata resolves).

### Watch folder lifecycle

`watch/` is a **drop zone only** — the pipeline never writes there. Once a file is fully processed, its watch copy is removed; SQLite keeps the track row, fingerprint, and duplicate-group membership for dedup and audit (`source_path` is immutable).

| Outcome | Watch copy | DB row |
|---------|------------|--------|
| Routed to **`ready/`** (or **Approve** from review) | Deleted | Kept |
| Non-preferred duplicate → **`duplicates/<hash>/`** | Deleted after fingerprint | Kept (`duplicate` status) |
| **`review/`** (loudness, quality, or metadata gate) | Kept until approve or reset | Kept |
| **Reset** (no watch file) | Restored from `ready/` or `review/` to original `source_path` | Kept; pipeline re-runs |

Re-dropping the same path while the track is already `ready`, `review`, `duplicate`, or `archived` does not re-ingest (queue dedup uses `source_path`).

Restart **API**, **worker**, **watcher**, and **frontend** after code changes.

---

## Deferred (later phases)

- MusicBrainz Picard CLI in Docker (pyacoustid used instead; Python orchestrates pipeline)
- Artwork embed from Cover Art Archive
- **MusicBrainz editor integration** — submit corrected tags/genres when approving review tracks (requires MB editor account; exploratory)
- Manual duplicate resolution — [PHASE5.md](./PHASE5.md)
- Backlog `POST /queue/tag-backlog` — Phase 7b in [PHASE6.md](./PHASE6.md)

---

## Exit criteria (Phase 4)

- [x] `pytest` green; rename + tag tests
- [x] Pipeline: `FINGERPRINT → TAG → ROUTE`
- [x] Renamed file in `ready/` uses `Title - Artist (Mix).ext`
- [x] Low-confidence / no-match tracks route to `review/` when flagged
- [x] Settings UI: naming template + confidence threshold
- [x] Genre/subgenre via MusicBrainz (recording → release → artist) + embedded tags; genre backfill API; re-resolve on manual edit; backfill on Approve
- [x] Dashboard pipeline step chips (`pipeline_stage`); WAV/AIFF ID3 tagging; editable artist/title/genre/subgenre; format/quality/bitrate in UI; loudness + quality gates in Settings
- [x] Docs updated: PHASE4, README, deploy troubleshooting

---

## References

- [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md)
- [PHASE3.md](./PHASE3.md)
- [ROADMAP.md](./ROADMAP.md)
