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

## Raspberry Pi — Docker Hub

**GitHub hosts the code; Docker Hub hosts the images.** Pushing to GitHub does not publish Docker images — you build and push **once from your Mac**, then the Pi only pulls.

### On your Mac (publish)

```bash
cd /path/to/dj
docker login -u YOUR_DOCKERHUB_USERNAME
DOCKER_USER=YOUR_DOCKERHUB_USERNAME ./deploy/publish-dockerhub.sh
```

Images: `YOUR_DOCKERHUB_USERNAME/dj-pipeline-backend:latest` and `...-frontend:latest` (built for **linux/arm64** by default).

### On the Pi (run)

```bash
mkdir -p ~/dj-pipeline && cd ~/dj-pipeline
curl -fsSLO https://raw.githubusercontent.com/hannibalov/dj/main/deploy/docker-compose.yml
printf 'DOCKER_USER=youruser\nDJ_ENV=production\nDJ_ACOUSTID_API_KEY=your_key\n' > .env
mkdir -p data/{watch,incoming,processing,ready,review,duplicates,archive,failed,logs,rekordbox}
docker compose pull && docker compose up -d
```

Open **http://\<pi-ip\>:5173** — full guide: [deploy/README.md](./deploy/README.md)

### Upgrade after a new image push

On the Pi (same folder as `docker-compose.yml`):

```bash
cd ~/dj-pipeline
docker compose pull && docker compose up -d
```

Then use dashboard **Reanalyze all** if you need to refresh loudness, BPM/key, tags, and routing (the **worker** container must be running). See [Dashboard](#dashboard).

### Which `docker-compose.yml`?

| File | Who uses it | What it does |
|------|-------------|--------------|
| **[deploy/docker-compose.yml](./deploy/docker-compose.yml)** | **Raspberry Pi / production** | Pulls pre-built images from Docker Hub (`DOCKER_USER/dj-pipeline-*`). No repo clone on the Pi — copy or `curl` this file only. |
| **[docker-compose.yml](./docker-compose.yml)** (repo root) | **Developers** | Builds images from source (`docker compose up -d --build`) with the full repo checked out. |
| **[docker-compose.pull.yml](./docker-compose.pull.yml)** | *Legacy — do not use* | Older pull-only file with full image URLs (`DJ_BACKEND_IMAGE` / `DJ_FRONTEND_IMAGE`). Superseded by `deploy/docker-compose.yml` + `DOCKER_USER`. |

You only need **one** compose file on a given machine. The Pi uses **`deploy/docker-compose.yml`**; local hacking uses the **root** file.

### Developers: build from source

Clone the repo and use root `docker compose up -d --build`, or see [Quick start (local development)](#quick-start-local-development) below.

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

`DJ_ACOUSTID_API_KEY` — **recommended** for fingerprint-based artist/title. Without it, tagging uses embedded tags, filename parsing, and **MusicBrainz text search** (artist/title from the watch filename) for metadata and genre. Worker needs HTTPS to `musicbrainz.org` (always) and `api.acoustid.org` (when key is set).

**Routing gates** (env defaults; editable in **Settings** and stored in SQLite):

| Variable | Default | Effect |
|----------|---------|--------|
| `DJ_REVIEW_LUFS_THRESHOLD` | `-18` | Integrated LUFS below this → `review/` |
| `DJ_REVIEW_TRUE_PEAK_DB` | `3.0` | True peak above this (dBTP) → `review/` |
| `DJ_REVIEW_MIN_MP3_BITRATE_KBPS` | `320` | MP3 below this kbps → `review/` (`0` = off) |
| `DJ_REVIEW_MIN_LOSSLESS_BIT_DEPTH` | `16` | Lossless below this bit depth → `review/` (`0` = off) |
| `DJ_REVIEW_MIN_LOSSLESS_SAMPLE_RATE_HZ` | `44100` | Lossless below this sample rate → `review/` (`0` = off) |

True peak uses ffmpeg `ebur128`. Decoded **MP3** often reports inter-sample peaks above 0 dBTP without audible distortion; the default **+3.0 dBTP** gate avoids flagging normal loud masters. Set **`0`** on any quality gate field in Settings to disable that check.

### Settings page

| Section | What it controls |
|---------|------------------|
| **Folders** | Watch, processing, ready, review, duplicates, etc. (SQLite overrides `.env`) |
| **Tagging & naming** | AcoustID confidence threshold, library filename template |
| **Loudness gates** | LUFS and true-peak thresholds for `review/` routing |
| **Quality gates** | Min MP3 bitrate, min lossless bit depth / sample rate for `review/` routing |

Restart **watcher** if you change `watch_folder`. Routing gates apply on the next **ROUTE** job (use **Reanalyze all** or per-track **Reset** to re-evaluate existing tracks).

---

## Dashboard

Open **http://\<host\>:5173** (Docker) or **http://localhost:5173** (local dev). Live updates via WebSocket.

### Actions (top bar)

| Button | What it does |
|--------|----------------|
| **Rescan watch folder** | Enqueue `INGEST` for new files in `watch/` |
| **Analyze backlog** | Enqueue `ANALYZE` for `ingested` tracks that have no LUFS yet |
| **Reanalyze all** | Full reprocess for every track with audio in `processing/` or `ready/`/`review/`: clears analysis + tag metadata, then **ANALYZE → FINGERPRINT → TAG → ROUTE** (requires **worker** running) |

### Pipeline card (track stages vs job queue)

Two different numbers:

| UI area | Meaning |
|---------|---------|
| **Songs by pipeline step** (chips) | **Track** progress in the database — counts **all** tracks via `by_pipeline_stage` (e.g. Awaiting analyze, Analyzed, Awaiting tag). Click a chip to filter the tracks table. |
| **Background jobs** | **Job** queue: pending / running / failed / completed. The worker drains **one job at a time**. |

Pipeline steps (worker order): **Queued** → **Ingesting** → **Awaiting analyze** → **Analyzed** → **Awaiting tag** → **Awaiting route** → **Ready** / **Review** / **Duplicate** / **Failed**.

After **Reanalyze all**, most tracks show **Awaiting analyze** until the worker reaches them; steps advance one job at a time (slow on a Pi with hundreds of tracks).

**Artist / title / genre / subgenre** appear after the **TAG** job (or on **Approve** for genre backfill). Until then those columns may show `—` even if loudness/BPM are filled in.

**Format**, **Quality** (bit depth / sample rate for lossless), and **Bitrate** (MP3 kbps) are read from the on-disk file when the dashboard loads (library copy → processing → watch). **Quality** and **Bitrate** are sortable; each column shows data for one format family only (lossless → Quality, MP3 → Bitrate, the other shows `—`).

The tracks table lists up to **500** newest tracks; the header shows **“table shows N newest”** when you have more in the DB.

### Worker card

| Status | Meaning |
|--------|---------|
| **Processing** | A job is `running` |
| **Backlogged** | Jobs are `pending` but none `running` (worker is between steps — normal on a Pi with a large queue) |
| **Stalled** | `pending` > 0 and `running` = 0 for a long time — worker may be stopped or jobs stuck in `running` |
| **Idle** | No pending jobs |

| Action | When to use |
|--------|-------------|
| **Retry stalled jobs** | Resets jobs stuck in `running` back to `pending` (e.g. after worker crash) |
| **Clear failed jobs** | Deletes all **failed** rows from the job history (does not delete tracks) |

### Tracks table

| Column / action | Notes |
|-----------------|--------|
| **Artist / Title** | Editable inline — blur or Enter saves via `PATCH /tracks/{id}/metadata`, rewrites file tags, renames in place per naming template, clears metadata-review flag |
| **Genre / Subgenre** | Filled at TAG via MusicBrainz (AcoustID ID or **artist/title search** from filename) + embedded tag fallback; **Approve** backfills if still empty |
| **Format / Quality / Bitrate** | From mutagen on the current audio path (not stored in DB). Quality = lossless bit depth + sample rate; Bitrate = MP3 kbps only |
| **Loudness** | From ffmpeg `ebur128` at ANALYZE. Badges: **OK**, **Too quiet** (LUFS below gate), **High peak** (true peak above gate). Thresholds match Settings → Loudness gates |
| **Reset** | Re-queue ingest |
| **Delete** | **Failed** tracks only |
| **Approve** | **Review** tracks → `ready/`; tries MusicBrainz genre lookup if missing |

Header **Clear N failed** removes all tracks in `failed` status (files + DB row).

Library filenames use **`Title - Artist (Mix).ext`** — that can look “reversed” compared to watch-folder names (`Artist - Title`), even when artist/title in the table are correct.

### Duplicate groups

**Keep** one copy per fingerprint group; others archived.

### Recent jobs

Last **200** jobs in the API snapshot (paginated in the UI). Check **Error** for failures (e.g. missing file, ffmpeg, tagging).

Common TAG errors:

| Error | Cause | Fix |
|-------|--------|-----|
| `'artist' not a Frame instance` on **tag** + `.wav` | Old builds used the wrong mutagen API for WAV/AIFF | Upgrade backend image; **Reanalyze all** |
| Tracks stuck on **Awaiting analyze**, worker **idle**, 0 pending | Earlier job failed; chain stopped | **Recent jobs** → fix cause → **Reanalyze all** or per-track **Reset** |
| **Analyze backlog** enqueues 0 | Backlog only targets `ingested` tracks **without LUFS** | Use **Reanalyze all** for analyzed-but-stuck tracks |
| No **genre** / **subgenre** | Empty embedded tags; old image before MB search | Upgrade backend; **Reanalyze all** or **Approve** review tracks |

### Operations checklist

1. **`docker compose ps`** — `worker` must be **Up** (or run `python -m app.workers.main` locally).
2. After a **backend image upgrade**, run **Reanalyze all** once if you fixed analysis/tagging/WAV tags; keep the worker up until **pending** hits 0.
3. Many **failed jobs** from an old bug? Fix/deploy, then **Clear failed jobs**. Reset or reanalyze stuck tracks (clearing failed jobs alone does not re-queue work).
4. Set **`DJ_ACOUSTID_API_KEY`** for best artist/title (fingerprint). Genre and low-confidence upgrades also use **MusicBrainz search** without a key (needs outbound HTTPS).

---

## API (summary)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET/PUT | `/settings` | Folders, tagging, loudness gates, quality gates |
| GET | `/pipeline/status` | Snapshot: queue, tracks (≤500), `track_summary` counts, worker flags |
| POST | `/queue/rescan` | Scan watch → ingest |
| POST | `/queue/analyze-backlog` | Analyze ingested tracks without LUFS |
| POST | `/queue/reanalyze-all` | Full reprocess: analyze → fingerprint → tag → route |
| POST | `/queue/unstick` | Reset `running` jobs → `pending` |
| POST | `/queue/clear-failed-jobs` | Delete all failed jobs from history |
| GET | `/duplicates` | Duplicate groups |
| POST | `/duplicates/resolve` | Keep one copy; archive others |
| GET | `/tracks` | List tracks (dashboard uses limit 500; includes `pipeline_stage`, format/bitrate from files) |
| PATCH | `/tracks/{id}/metadata` | Manual artist/title override → write tags + rename |
| POST | `/tracks/{id}/reset` | Reset track; re-enqueue ingest |
| POST | `/tracks/{id}/confirm-review` | Move review → ready |
| DELETE | `/tracks/{id}` | Delete track (failed status only) |
| POST | `/tracks/delete-failed` | Bulk delete all failed tracks |
| WS | `/ws` | Pipeline push (proxied at `/ws` in Docker UI) |

---

## Tests & lint

```bash
make test      # backend + frontend (see CI or `make test` for current counts)
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
| Later | PHASE6 backlog | Duplicate compare + waveforms (5b), tag backlog + retries (5c), duplicate-rule settings (5d remainder) |
| Later | — | Essentia on ARM, `GET /logs`, metrics dashboard |

---

## Core principles

1. **Never process in place** — watch → processing → library folders.
2. **Queue-based** — watcher enqueues; workers process.
3. **Docker-first** for deployment on Pi.
4. **TDD** — tests before new modules.

## License

Private project — add a license if you open-source it.
