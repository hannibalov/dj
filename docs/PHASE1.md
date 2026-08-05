# Phase 1 — Foundation & ingest pipeline

**Status: complete** (May 2026)

**Goal:** A deployable skeleton that watches a folder, waits for sync stability, enqueues jobs, copies files into a processing workspace, and exposes settings + live dashboard status. No audio analysis, fingerprinting, or Rekordbox routing.

---

## What was delivered

### Backend

- FastAPI app with SQLite (`jobs`, `tracks`, `settings`)
- **Watcher** → enqueues `INGEST` jobs only (never copies in watch folder)
- **Worker** → stability check → copy to `processing/` → track status `ingested`
- **Queue deduplication** — skips enqueue when job is already pending/running or track is already ingested
- **Idempotent ingest** — will not create `_2`, `_3` copies on rescan if processing file exists
- **Rescan** — `POST /queue/rescan` returns `{ enqueued, skipped }`
- Settings: `.env` defaults + UI overrides in DB (UI wins)
- Structured JSON logs (`WATCHER`, `API`, `ROUTER`, `ANALYZER`)
- Worker → API notify via `DJ_API_INTERNAL_URL` for live UI updates

### Frontend

- Vue 3 + TypeScript + Vuetify
- **Settings** — all folder paths
- **Dashboard** — queue stats, worker status + last event, **tracks table**, **jobs table**
- **WebSocket** — `ws://host/ws` (proxied in Vite dev) pushes full pipeline snapshot on change
- Pinia `pipelineStore`, Vitest for settings store

### Tooling

- `make test`, `make lint`, `scripts/install.py` writes local `.env` under `./data/`
- Docker Compose with `/data/...` overrides via `environment:` block
- pytest includes queue dedup + idempotent ingest tests

---

## Track & job lifecycle (Phase 1)

| Track status | Meaning |
|--------------|---------|
| `queued` | Known to DB, not yet ingesting |
| `processing` | Worker is actively ingesting (stability wait or copy) |
| `ingested` | Copy exists in `processing/`; **ingest step done** (analysis not started) |
| `failed` | Ingest failed |

| Job status | Meaning |
|------------|---------|
| `pending` / `running` / `completed` / `failed` | Standard queue job state |

**Important:** `ingested` does **not** mean the full pipeline is finished — only that Phase 1 ingest completed. Phase 2 adds analysis and routing.

---

## Out of scope (deferred to Phase 2+)

- Essentia BPM/key/energy analysis
- Chromaprint / duplicate resolution
- MusicBrainz Picard tagging
- Routing to ready / review / duplicates / archive
- Duplicate resolution UI, waveforms
- Dashboard CPU/RAM metrics
- Full Docker image with Essentia + Picard
- Scheduler retries (scheduler is heartbeat-only)

---

## Test checklist (exit criteria)

- [x] `pytest` green in `backend/`
- [x] `npm test` + `make lint` green in `frontend/`
- [x] Drop file in `data/watch/` → queue → copy in `data/processing/`
- [x] Rescan does not duplicate already-ingested files
- [x] Settings UI persists folder paths; watcher needs restart after `watch_folder` change
- [x] Worker survives API restart; queue persists in SQLite
- [x] No writes inside watch folder (copy only)

---

## Operational notes

### Restart after code changes

Restart **API**, **worker**, **watcher**, and **frontend** (`npm run dev` for `/ws` proxy). `uvicorn --reload` alone is not enough for workers.

### Configuration

- **`.env`** — local dev paths under `<repo>/data/` (written by `scripts/install.py`)
- **Docker** — `docker-compose.yml` `x-docker-env` sets `/data/...`
- **UI** — overrides stored in SQLite `settings` table; restart watcher if `watch_folder` changes

---

## Known follow-ups (optional polish)

- DB unique constraint on one pending ingest job per `source_path`
- Failed job retry with backoff in scheduler
- API auth for `/internal/pipeline-notify`
- `GET /logs` implementation
- Migrate old DB rows stuck on `processing` → `ingested` after manual file cleanup

---

## Later phases

| Phase | Doc | Status |
|-------|-----|--------|
| 2 — Analysis & routing | [PHASE2.md](./PHASE2.md) | **Complete** |
| 3 — Fingerprints & duplicates | [PHASE3.md](./PHASE3.md) | **Complete** |
| 4 — Tagging & **renaming** | [PHASE4.md](./PHASE4.md) | **Next** |
| Overview | [ROADMAP.md](./ROADMAP.md) | |
