# Phase 2 — Audio analysis & routing

**Status: complete** (May 2026)

**Prerequisite:** Phase 1 — [PHASE1.md](./PHASE1.md). **Next:** [PHASE4.md](./PHASE4.md) (tagging & renaming).

---

## Goal

After ingest (`track.status == ingested`), run analysis and route tracks to `ready` or `review` based on loudness rules.

**Filenames are unchanged** — copies keep the original basename. Metadata renaming is [Phase 4](./PHASE4.md).

---

## What was delivered

### Backend — analysis

| Area | Location |
|------|----------|
| Loudness (ffmpeg `ebur128`) | `backend/app/analysis/loudness.py` |
| BPM / key (Essentia in Docker) | `backend/app/analysis/musical.py` |
| Energy 0–100 (from LUFS) | `backend/app/analysis/analyzer.py` |
| Camelot mapping | `backend/app/analysis/camelot.py` |
| Orchestration | `backend/app/analysis/analyzer.py` |
| Result type | `backend/app/analysis/result.py` |

**Track columns added:** `scale`, `bpm_confidence`, `key_confidence`, `integrated_lufs`, `true_peak_db` (plus existing `bpm`, `musical_key`, `camelot`, `energy`).

**Migration:** `backend/app/db/migrate.py` — additive SQLite `ALTER TABLE`; runs from `create_tables()` on API startup and in tests.

### Backend — routing & jobs

| Area | Location |
|------|----------|
| Review rules (LUFS / true peak / quality) | `backend/app/router/rules.py` |
| Route job handler | `backend/app/services/routing_service.py` |
| Analyze job handler | `backend/app/services/analysis_service.py` |
| Queue: analyze/route dedup + backlog | `backend/app/services/queue_service.py` |
| Worker chain | `backend/app/workers/main.py` |

**Job chain (at Phase 2 ship):** `INGEST` → `ANALYZE` → `ROUTE` (enqueued automatically on success).

**After Phase 3:** analyze enqueues `FINGERPRINT` instead of `ROUTE`; routing runs after fingerprint/duplicate resolution. See [PHASE3.md](./PHASE3.md).

**Config:** `DJ_REVIEW_LUFS_THRESHOLD` (default `-18`), `DJ_REVIEW_TRUE_PEAK_DB` (default `3.0` dBTP). MP3 inter-sample peaks from ffmpeg `ebur128` commonly exceed 0 dBTP without audible clipping; `-0.1` was too strict for MP3-heavy libraries.

### Backend — API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/queue/analyze-backlog` | Enqueue `ANALYZE` for `ingested` tracks without `integrated_lufs` |
| POST | `/queue/reanalyze-all` | Full reprocess: `ANALYZE` → `FINGERPRINT` → `TAG` → `ROUTE` with `reprocess` payload |
| POST | `/queue/genre-backfill` | Re-fetch missing genre/subgenre for tagged tracks (inline MusicBrainz) |
| POST | `/queue/unstick` | Reset interrupted `running` jobs → `pending` |
| POST | `/queue/clear-failed-jobs` | Remove failed job rows from history |

### Frontend — dashboard

| Feature | Location |
|---------|----------|
| Action bar (top) | `frontend/src/components/DashboardActions.vue` |
| Pipeline stage counts (all tracks in DB) | `frontend/src/components/QueueStatsCard.vue`, `utils/pipelineCounts.ts` |
| Worker: Processing / Backlogged / Stalled | `frontend/src/components/WorkerStatusCard.vue` |
| Rescan, Analyze backlog, Reanalyze all | `DashboardPage.vue` |
| Tracks: BPM, key, energy, **loudness**, editable artist/title/genre/subgenre, format/quality/bitrate (sortable) | `frontend/src/components/TracksTable.vue` |
| Delete failed track; filter by stage chip | `TracksTable.vue`, `trackService.ts` |
| Clear failed jobs / Clear failed tracks | `QueueStatsCard.vue`, `WorkerStatusCard.vue` |
| Loudness helpers (thresholds from Settings, labels) | `frontend/src/utils/loudness.ts` |
| Global snackbars (10s auto-dismiss) | `frontend/src/stores/snackbarStore.ts`, `AppSnackbar.vue` |
| Pipeline feedback via snackbar | `frontend/src/stores/pipelineStore.ts` |
| Full-height layout / background | `frontend/src/styles/main.css`, `App.vue` |

Snackbar colors: success (rescan/backlog OK), error (failures). See [README § Dashboard](../README.md#dashboard) for operator guide.

**Tagging note:** `app/metadata/acoustid_lookup.py` must call `acoustid.parse_lookup_result()` on the JSON from `acoustid.lookup()` — not `list()` on the raw dict (regression caused TAG failures: “too many values to unpack”).

### Tests

**Backend (20):** `test_router_rules`, `test_routing_service`, `test_analysis_service`, `test_camelot`, `test_queue_dedup`, plus Phase 1 tests.

**Frontend (7):** `pipelineStore`, `snackbarStore`, `loudness`, `settingsStore`.

```bash
make test   # backend + frontend
make lint
```

---

## Track & job lifecycle (Phase 2)

| Track status | Meaning |
|--------------|---------|
| `ingested` | In `processing/`; analysis may be pending or done |
| `ready` | Copied to `ready/` after loudness, quality, and metadata gates pass |
| `review` | Copied to `review/` (too quiet, high peak, below min quality, or metadata review) |

| Job types used | `ingest`, `analyze`, `route` |

---

## Deferred

- ~~Essentia preinstalled in Docker image (ARM/Pi)~~ — done in `docker/Dockerfile.backend`
- Worker CPU/RAM limits enforced during analysis
- Duplicate-rule settings UI (see [PHASE6 backlog](./PHASE6.md#backlog-from-earlier-phases))
- Split “loudness gate” vs “final library route” when Phase 4 adds tagging (Phase 3 added fingerprint + `duplicates/` routing)

**Delivered after Phase 2:** Loudness and quality gate thresholds editable in Settings UI (`LoudnessSettingsForm`, `QualitySettingsForm`).

---

## Operational notes

### Restart after code changes

Restart **API**, **worker**, **watcher**, and **frontend**. API runs `create_tables()` + migration on startup.

### Essentia (BPM / key / energy)

**Docker:** Essentia is built into `docker/Dockerfile.backend` (no extra setup on Pi).

**Local dev:** optional — install Essentia on the host, or use Docker. Without Essentia, loudness + routing still work (ffmpeg only); BPM/key columns stay empty.

```bash
conda install -c mtg essentia   # example for local dev
```

### Backlog analysis

- Dashboard → **Analyze backlog**, or  
- `curl -X POST http://127.0.0.1:8000/queue/analyze-backlog`

**Rescan watch folder** only enqueues **INGEST** for new watch files.

### Requirements

- `ffmpeg` on `PATH` for the worker process
- Worker running while jobs are pending

---

## References

- [ROADMAP.md](./ROADMAP.md)
- [PHASE3.md](./PHASE3.md)
- [PHASE4.md](./PHASE4.md)
- [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md)
