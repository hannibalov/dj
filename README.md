# DJ Library Pipeline

Self-hosted, fire-and-forget DJ library ingestion and organization for Raspberry Pi 4 and Docker. Watches a synced music folder (e.g. Nextcloud), queues work safely, copies files into a processing workspace (never in place), analyzes loudness, fingerprints duplicates, and routes tracks into `ready/`, `review/`, or `duplicates/` — with tagging and renaming planned in Phase 4.

| Document | Purpose |
|----------|---------|
| [dj-library-pipeline-spec.md](./dj-library-pipeline-spec.md) | Full product specification |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Phased roadmap |
| [docs/PHASE1.md](./docs/PHASE1.md) | Phase 1 (ingest) — **complete** |
| [docs/PHASE2.md](./docs/PHASE2.md) | Phase 2 (analysis & routing) — **complete** |
| [docs/PHASE3.md](./docs/PHASE3.md) | Phase 3 (fingerprints & duplicates) — **complete** |
| [docs/PHASE4.md](./docs/PHASE4.md) | Phase 4 (tagging & **renaming**) — **start here** |

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite, watchdog, structlog, httpx |
| Frontend | Vue 3, Vite, TypeScript, Pinia, Vuetify, Vitest |
| Analysis | ffmpeg (required), Essentia (optional), Chromaprint/fpcalc (fingerprints), Picard (Phase 4) |
| Runtime | Docker Compose |

## Repository layout

```text
backend/app/analysis/    Phase 2 — loudness, BPM/key, Camelot
backend/app/router/      Phase 2 — review vs ready rules
backend/app/fingerprint/ Phase 3 — Chromaprint, duplicate detection
backend/app/metadata/    Phase 4 placeholder
frontend/                Vue 3 + TypeScript UI
data/                    Runtime folders + SQLite (gitignored)
docs/                    Phase plans (PHASE1–4, ROADMAP)
```

## Quick start (local development)

### 1. Install

```bash
chmod +x install.sh
./install.sh
```

Creates `data/*`, Python venv, `data/dj_library.db`, npm deps, and `.env` with paths under `./data/`.

**Does not install** system audio tools — see [System dependencies](#system-dependencies) below.

```bash
cd /path/to/dj
set -a && source .env && set +a
```

### System dependencies

| Tool | Used for | Local dev (`./install.sh`) | Docker (`docker/Dockerfile.backend`) |
|------|----------|----------------------------|--------------------------------------|
| **ffmpeg** | Loudness analysis (required) | Install yourself | Preinstalled |
| **fpcalc** (Chromaprint) | Fingerprints & duplicates (required) | Install yourself | Preinstalled (`libchromaprint-tools`) |
| **Essentia** | BPM / key / energy (optional) | Optional | Not bundled on ARM/Pi yet |

```bash
# macOS
brew install ffmpeg chromaprint

# Debian/Ubuntu
sudo apt install ffmpeg libchromaprint-tools
```

Without `fpcalc`, `FINGERPRINT` jobs fail; without `ffmpeg`, `ANALYZE` fails.

### 2. Run (four terminals)

| Process | Command |
|---------|---------|
| API | `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| Worker | `python -m app.workers.main` |
| Watcher | `python -m app.workers.watcher` |
| Frontend | `cd frontend && npm run dev` |

Open http://localhost:5173 — REST via `/api`, WebSocket at `/ws`.

### 3. Try it

1. Copy audio to `data/watch/`.
2. Wait for stability (~10s) — worker runs **ingest → analyze → fingerprint → route**.
3. Dashboard updates live: **Loudness** (LUFS + peak), **Duplicate groups** (when fingerprints match).
4. Preferred copies land in `data/ready/` or `data/review/`; extra duplicates in `data/duplicates/<hash>/`. **Filenames stay as uploaded** until Phase 4 tagging/renaming.

For tracks already ingested before analysis: click **Analyze backlog** on the dashboard (enqueues `ANALYZE` only; fingerprint and route follow automatically).

See [PHASE2.md](./docs/PHASE2.md) (analysis) and [PHASE3.md](./docs/PHASE3.md) (fingerprints).

---

## Dashboard (current UI)

- **Top action bar:** Rescan watch folder · Analyze backlog
- **Snackbar feedback:** success/error messages, auto-dismiss after 10s (bottom-right)
- **Tracks table:** status filter; BPM, key, energy, loudness (chip + LUFS/peak), library copy path
- **Duplicate groups:** fingerprint hash, format/bitrate per member, status chips
- **Jobs table:** pending/running/completed ingest, analyze, fingerprint, route jobs
- **Queue & worker cards:** counts and last WebSocket event

---

## Configuration

| Source | Role |
|--------|------|
| `.env` | Defaults (`./data/...` locally) |
| Settings UI | SQLite overrides (win over `.env`) |
| docker-compose | `/data/...` in containers |

Restart **watcher** after changing `watch_folder` in the UI.

`DJ_REVIEW_LUFS_THRESHOLD` / `DJ_REVIEW_TRUE_PEAK_DB` — loudness routing (defaults `-18` LUFS, `-0.1` dBTP).

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET/PUT | `/settings` | Folder paths + stability |
| GET | `/pipeline/status` | Queue + tracks + worker snapshot |
| GET | `/queue` | Queue summary |
| POST | `/queue/rescan` | Scan watch folder → `INGEST` jobs |
| POST | `/queue/analyze-backlog` | `ANALYZE` for ingested tracks without LUFS |
| GET | `/tracks`, `/tracks/{id}` | Track list/detail |
| GET | `/duplicates` | Duplicate groups (2+ tracks, format/bitrate per member) |
| POST | `/duplicates/resolve` | Stub — manual resolution later |
| GET | `/logs` | Stub |
| WS | `/ws` | Pipeline snapshot push |
| POST | `/internal/pipeline-notify` | Worker → UI refresh |

---

## Resetting local state

```bash
# Stop worker, watcher, API first
rm -f data/dj_library.db
rm -f data/processing/* data/ready/* data/review/* data/duplicates/*/*
cd backend && source .venv/bin/activate && set -a && source ../.env && set +a
python -m app.db.init_db
```

Deleting files without resetting the DB leaves stale `tracks`/`jobs` rows.

---

## Tests & lint

```bash
make test      # 28 backend + 8 frontend tests
make lint
make lint-fix
```

---

## Current pipeline (Phases 1–3)

```text
watch → INGEST → ANALYZE → FINGERPRINT → ROUTE
                              ↓
                    duplicates/<hash>/  (non-preferred)
                    ready/ or review/   (preferred, loudness rules)
```

## What’s next (Phase 4)

MusicBrainz / Picard tagging, **file renaming** (`Title - Artist (Mix).ext`), final metadata in `ready/`. See [docs/PHASE4.md](./docs/PHASE4.md).

**Not yet:** manual duplicate resolution UI, `POST /duplicates/resolve`, Picard in Docker image.

---

## Core principles

1. **Never process in place** — watch → processing → library folders.
2. **Queue-based** — watcher enqueues; workers process jobs.
3. **TDD** — tests before new modules.
4. **Docker-first** for deployment.

## License

Private project — add a license if you open-source it.
