# DJ Library Pipeline

Self-hosted DJ library ingestion for **Raspberry Pi 4** and Docker. Watches a synced folder (e.g. Nextcloud), queues work safely, copies into a processing workspace (never in place), analyzes loudness, fingerprints duplicates, tags/renames via AcoustID, and routes tracks to `ready/`, `review/`, `duplicates/`, or `archive/`.

| Document | Purpose |
|----------|---------|
| [dj-library-pipeline-spec.md](./dj-library-pipeline-spec.md) | Full product specification |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Phased roadmap |
| [docs/PHASE6.md](./docs/PHASE6.md) | **Next:** Docker on Pi — deployment plan |
| [docs/PHASE1.md](./docs/PHASE1.md) – [PHASE5.md](./docs/PHASE5.md) | Completed phase notes |

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite, watchdog, structlog |
| Frontend | Vue 3, Vite, TypeScript, Pinia, Vuetify |
| Analysis | ffmpeg, Chromaprint (`fpcalc`), pyacoustid; Essentia optional (not in Docker yet) |
| Runtime | **Docker Compose** (recommended for Pi) |

## Current pipeline (Phases 1–5)

```text
watch → INGEST → ANALYZE → FINGERPRINT → TAG → ROUTE
                              ↓
                    duplicates/<hash>/   (non-preferred)
                    ready/ or review/    (preferred, after tag + loudness)
```

Manual duplicate resolution: dashboard **Keep** → `POST /duplicates/resolve` → archive others, re-tag keeper.

---

## Docker (Raspberry Pi / server)

**Recommended for 24/7 use on a Pi.** Images include ffmpeg and fpcalc; no host Python required.

### Requirements

| Item | Notes |
|------|--------|
| OS | Raspberry Pi OS **64-bit** (or any Linux `arm64`/`amd64` host) |
| Docker | Engine 24+ and Compose v2.24+ (for optional registry override file) |
| RAM | 2 GB minimum; 4 GB+ comfortable with worker analyzing large files |
| Disk | Persistent volume for `data/` (SQLite + audio folders) |

### 1. Prepare on the Pi

```bash
git clone <your-repo-url> dj && cd dj

cp env.docker.example .env
# Edit .env — set DJ_ACOUSTID_API_KEY (https://acoustid.org/new-application)

mkdir -p data/{watch,incoming,processing,ready,review,duplicates,archive,failed,logs,rekordbox}
```

**Optional — point watch at a sync folder** (e.g. Nextcloud):

```yaml
# In docker-compose.yml, under api/worker/watcher volumes, add:
#   - /home/pi/nextcloud/Music/Dropbox:/data/watch
```

Or symlink: `ln -s /path/to/sync/folder data/watch`

### 2. Build and run

```bash
docker compose up -d --build
```

| Service | Role |
|---------|------|
| `api` | FastAPI on port 8000 (internal + host) |
| `worker` | Job queue processor |
| `watcher` | Watch folder → ingest jobs |
| `scheduler` | Heartbeat / future retries |
| `frontend` | nginx UI on port **5173** |
| `db-init` | One-shot SQLite init (runs once) |

Open **http://\<pi-ip\>:5173** — UI proxies `/api` and `/ws` to the API container.

### 3. Try it

1. Copy audio into `data/watch/` (or your mounted sync path).
2. Wait ~10s for stability, then watch the dashboard (live WebSocket updates).
3. Preferred copies end in `data/ready/` as `Title - Artist (Mix).ext` after tagging.
4. Duplicates appear under **Duplicate groups** — use **Keep** to override auto-preference.

### 4. Logs and lifecycle

```bash
docker compose ps
docker compose logs -f worker
docker compose restart worker watcher api
docker compose down          # stop (data/ persists)
docker compose up -d --build # upgrade after git pull
```

### 5. Publish images (build on Mac/CI, run on Pi)

On a machine with [Docker Buildx](https://docs.docker.com/build/building/multi-platform/):

```bash
export REGISTRY=ghcr.io/youruser/dj-pipeline   # adjust

docker buildx build --platform linux/arm64 -f docker/Dockerfile.backend \
  -t ${REGISTRY}-backend:latest --push .

docker buildx build --platform linux/arm64 -f docker/Dockerfile.frontend \
  -t ${REGISTRY}-frontend:latest --push .
```

On the **Pi** (pull instead of build):

```bash
export DJ_BACKEND_IMAGE=ghcr.io/youruser/dj-pipeline-backend:latest
export DJ_FRONTEND_IMAGE=ghcr.io/youruser/dj-pipeline-frontend:latest
docker compose -f docker-compose.pull.yml pull
docker compose -f docker-compose.pull.yml up -d
```

Native build on the Pi (`docker compose up -d --build`) avoids a registry and is fine for personal use.

### Docker vs local paths

| Setting | In container | On host (default compose) |
|---------|----------------|---------------------------|
| Database | `/data/dj_library.db` | `./data/dj_library.db` |
| Watch | `/data/watch` | `./data/watch` |
| Ready | `/data/ready` | `./data/ready` |

`docker-compose.yml` sets `DJ_*_FOLDER=/data/...`; the bind mount `./data:/data` maps them to your host tree.

---

## Quick start (local development)

For hacking on the codebase without Docker.

### 1. Install

```bash
chmod +x install.sh && ./install.sh
cd /path/to/dj && set -a && source .env && set +a
```

Creates `data/*`, Python venv, SQLite, npm deps. **Does not** install ffmpeg/fpcalc — see below.

### System dependencies (local only)

```bash
# macOS
brew install ffmpeg chromaprint

# Debian/Ubuntu / Raspberry Pi OS (dev on Pi without Docker)
sudo apt install ffmpeg libchromaprint-tools
```

| Tool | Required for |
|------|----------------|
| ffmpeg | Loudness analysis |
| fpcalc | Fingerprints & duplicates |
| Essentia | BPM/key (optional; not in Docker image yet) |

### 2. Run (four terminals)

| Process | Command |
|---------|---------|
| API | `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| Worker | `python -m app.workers.main` |
| Watcher | `python -m app.workers.watcher` |
| Frontend | `cd frontend && npm run dev` |

Open http://localhost:5173

---

## Configuration

| Source | Role |
|--------|------|
| `.env` | Secrets and overrides (`env.docker.example` for Docker) |
| Settings UI | SQLite folder paths (override `.env`; restart watcher if `watch_folder` changes) |
| `docker-compose.yml` | `/data/...` paths and service limits |

`DJ_ACOUSTID_API_KEY` — tagging without it falls back to embedded tags / filename parsing.

`DJ_REVIEW_LUFS_THRESHOLD` / `DJ_REVIEW_TRUE_PEAK_DB` — loudness routing (defaults `-18` LUFS, `-0.1` dBTP).

---

## Dashboard

- **Rescan watch** · **Analyze backlog**
- **Tracks:** status, BPM, key, loudness, artist/title, metadata review chip
- **Duplicate groups:** format, LUFS, **Keep** + archive others
- **Jobs** and queue stats; WebSocket live updates

---

## API (summary)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET/PUT | `/settings` | Folders + tagging thresholds |
| GET | `/pipeline/status` | Full snapshot |
| POST | `/queue/rescan` | Scan watch → ingest |
| POST | `/queue/analyze-backlog` | Analyze ingested tracks without LUFS |
| GET | `/duplicates` | Duplicate groups |
| POST | `/duplicates/resolve` | Keep one copy; archive others |
| POST | `/tracks/{id}/reset` | Reset track pipeline |
| POST | `/tracks/{id}/confirm-review` | Move review → ready |
| WS | `/ws` | Pipeline push (proxied at `/ws` in Docker UI) |

---

## Tests & lint

```bash
make test      # 60 backend + 9 frontend
make lint
```

---

## Resetting state

```bash
# Stop all processes / docker compose down first
rm -f data/dj_library.db data/processing/* data/ready/* data/review/* data/duplicates/*/*
# Docker: db-init runs on next compose up, or:
docker compose run --rm db-init
```

---

## What’s next

| Priority | Doc | Topic |
|----------|-----|--------|
| **Now** | [PHASE6.md](./docs/PHASE6.md) | Docker on Pi (6a) |
| Later | PHASE6 backlog | Duplicate compare + waveforms (5b), tag backlog + retries (5c), settings UI (5d) |
| Later | — | Essentia on ARM, `GET /logs`, metrics dashboard |

---

## Core principles

1. **Never process in place** — watch → processing → library folders.
2. **Queue-based** — watcher enqueues; workers process.
3. **Docker-first** for deployment on Pi.
4. **TDD** — tests before new modules.

## License

Private project — add a license if you open-source it.
