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
| BPM / key / energy (Essentia, optional) | `backend/app/analysis/musical.py` |
| Camelot mapping | `backend/app/analysis/camelot.py` |
| Orchestration | `backend/app/analysis/analyzer.py` |
| Result type | `backend/app/analysis/result.py` |

**Track columns added:** `scale`, `bpm_confidence`, `key_confidence`, `integrated_lufs`, `true_peak_db` (plus existing `bpm`, `musical_key`, `camelot`, `energy`).

**Migration:** `backend/app/db/migrate.py` — additive SQLite `ALTER TABLE`; runs from `create_tables()` on API startup and in tests.

### Backend — routing & jobs

| Area | Location |
|------|----------|
| Review rules (LUFS / true peak) | `backend/app/router/rules.py` |
| Route job handler | `backend/app/services/routing_service.py` |
| Analyze job handler | `backend/app/services/analysis_service.py` |
| Queue: analyze/route dedup + backlog | `backend/app/services/queue_service.py` |
| Worker chain | `backend/app/workers/main.py` |

**Job chain (at Phase 2 ship):** `INGEST` → `ANALYZE` → `ROUTE` (enqueued automatically on success).

**After Phase 3:** analyze enqueues `FINGERPRINT` instead of `ROUTE`; routing runs after fingerprint/duplicate resolution. See [PHASE3.md](./PHASE3.md).

**Config:** `DJ_REVIEW_LUFS_THRESHOLD` (default `-18`), `DJ_REVIEW_TRUE_PEAK_DB` (default `-0.1`).

### Backend — API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/queue/analyze-backlog` | Enqueue `ANALYZE` for `ingested` tracks without `integrated_lufs` |

### Frontend — dashboard

| Feature | Location |
|---------|----------|
| Action bar (top) | `frontend/src/components/DashboardActions.vue` |
| Rescan + Analyze backlog buttons | `DashboardPage.vue` |
| Tracks: BPM, key, energy, **loudness** (chip + LUFS/peak) | `frontend/src/components/TracksTable.vue` |
| Loudness helpers (thresholds, labels) | `frontend/src/utils/loudness.ts` |
| Status filter | `TracksTable.vue` |
| Global snackbars (10s auto-dismiss) | `frontend/src/stores/snackbarStore.ts`, `AppSnackbar.vue` |
| Pipeline feedback via snackbar | `frontend/src/stores/pipelineStore.ts` |
| Full-height layout / background | `frontend/src/styles/main.css`, `App.vue` |

Snackbar colors: success (rescan/backlog OK), error (failures). No inline alerts on the dashboard for queue actions.

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
| `ready` | Copied to `ready/` after loudness OK |
| `review` | Copied to `review/` (too quiet or clipped) |

| Job types used | `ingest`, `analyze`, `route` |

---

## Deferred

- Essentia preinstalled in Docker image (ARM/Pi)
- Worker CPU/RAM limits enforced during analysis
- Loudness thresholds editable in Settings UI
- Split “loudness gate” vs “final library route” when Phase 4 adds tagging (Phase 3 added fingerprint + `duplicates/` routing)

---

## Operational notes

### Restart after code changes

Restart **API**, **worker**, **watcher**, and **frontend**. API runs `create_tables()` + migration on startup.

### Essentia (optional)

Loudness + routing work with **ffmpeg only**. BPM/key need Essentia:

```bash
conda install -c mtg essentia   # example
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
