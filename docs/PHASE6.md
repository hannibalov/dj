# Phase 6 — Docker deployment (Raspberry Pi)

**Status: in progress (6a — May 2026)**

**Prerequisite:** Phase 5a — [PHASE5.md](./PHASE5.md) (duplicate resolution).

**Next after 6a:** Phase 5 backlog (compare UX, ops polish) or Phase 7 ops features — see [Backlog from earlier phases](#backlog-from-earlier-phases).

---

## Goal

Run the full pipeline on a **Raspberry Pi 4 (ARM64)** (or any Linux host) as prebuilt Docker images: API, worker, watcher, scheduler, and UI — with **no manual install** of ffmpeg, fpcalc, or Python on the host.

This answers: *“I synced new tracks to my Pi’s watch folder — how do I run the pipeline 24/7 without SSHing in to start five processes?”*

---

## Backlog from earlier phases

Items deferred while shipping core pipeline features. **Not part of Phase 6a** unless noted.

### Phase 5 — not done in 5a

| ID | Feature | Notes | Suggested phase |
|----|---------|--------|-----------------|
| **5b** | Side-by-side duplicate compare | BPM, key, LUFS, duration, tag confidence in one panel | 7a |
| **5b** | Waveform preview | `GET /tracks/:id/waveform` (ffmpeg peaks); embed in compare UI | 7a |
| **5b** | Audio A/B playback | Explicitly out of scope for v1 | — |
| **5c** | `POST /queue/tag-backlog` | TAG for `tagged_at IS NULL` in `processing/` | 7b |
| **5c** | Scheduler retries | Re-enqueue `FAILED` jobs with backoff + cap | 7b |
| **5c** | Failed job retry count in UI | Jobs table column / chip | 7b |
| **5d** | Loudness thresholds in Settings UI | `DJ_REVIEW_LUFS_THRESHOLD`, `DJ_REVIEW_TRUE_PEAK_DB` today via env only | 7c |
| **5d** | Duplicate rule toggle | User-configurable “FLAC + MP3 keep both” vs single keeper | 7c |

### Cross-phase / spec — still open

| Item | Source | Notes |
|------|--------|--------|
| Essentia in Docker on ARM/Pi | Phase 2, spec | BPM/key optional; loudness uses ffmpeg only |
| MusicBrainz Picard CLI in container | Phase 4 defer | pyacoustid used instead |
| Artwork embed (Cover Art Archive) | Phase 4 defer | |
| `GET /logs` | Phase 1+ | Stub in API |
| Dashboard CPU/RAM metrics | Spec | Worker limits in compose today; no UI gauges |
| API auth on `/internal/pipeline-notify` | Phase 1 polish | |
| DB unique constraint on pending ingest per `source_path` | Phase 1 polish | |
| Auto-delete duplicates | Spec out of scope | |
| Beatgrid / Rekordbox analysis replacement | Spec out of scope | |
| Smart playlists / AI | Spec out of scope | |

### Recommended order after Phase 6a

```text
6a  Docker on Pi (images, compose, README, WS proxy)     ← current
7a  Duplicate compare panel + waveform (5b)
7b  Tag backlog + scheduler retries (5c)
7c  Settings UI for loudness + duplicate rules (5d)
7d  Essentia on ARM (optional BPM/key in container)
8+  Logs API, metrics dashboard, Picard/artwork
```

---

## Phase 6a — scope (minimum shippable)

### Delivered / in this milestone

| Area | Item |
|------|------|
| Images | `docker/Dockerfile.backend` (ffmpeg + fpcalc, production pip install) |
| Images | `docker/Dockerfile.frontend` (nginx static + API/WS proxy) |
| Compose | `docker-compose.yml` — api, worker, watcher, scheduler, frontend, db-init |
| Networking | nginx proxies `/api` and `/ws` to API container |
| Docs | README — build, run, Pi mount paths, registry push |
| Docs | This file + [ROADMAP.md](./ROADMAP.md) |

### Host requirements (Pi)

| Requirement | Notes |
|-------------|--------|
| Docker Engine + Compose v2 | Raspberry Pi OS 64-bit recommended |
| `linux/arm64` | Native build on Pi; or `buildx` from amd64 Mac/CI |
| Disk | Bind-mount for `data/` (SQLite + library folders) |
| Watch folder | Often a Nextcloud/sync mount → map to `/data/watch` |
| `.env` | Copy `env.docker.example`; set `DJ_ACOUSTID_API_KEY` for tagging |

### Services (unchanged architecture)

```text
┌─────────────┐     ┌──────────┐     ┌─────────┐
│  frontend   │────▶│   api    │◀────│ worker  │
│  (nginx)    │     │ FastAPI  │     │ watcher │
└─────────────┘     └──────────┘     │scheduler│
       :5173              │          └─────────┘
                          ▼
                    /data (volume)
                    watch → … → ready/
```

### Environment

- Container paths use `/data/...` (see `docker-compose.yml` `x-docker-env`).
- `env.docker.example` documents Pi-friendly overrides.
- **Do not** bind-mount `.env` secrets into a public image; use host `.env` at runtime only.

### Resource limits (compose defaults)

| Service | CPU | Memory |
|---------|-----|--------|
| api | 1.0 | 512m |
| worker | 1.0 | 1g |
| watcher | 0.5 | 256m |
| scheduler | 0.25 | 128m |

Tune on Pi 4 if OOM — worker is the heaviest (ffmpeg analyze).

### Out of scope for 6a

- Multi-arch manifest publishing to Docker Hub (documented; CI not required)
- Kubernetes / Swarm
- Essentia inside the image
- TLS / reverse proxy (Traefik/Caddy) — user can front nginx with their own proxy
- ARMv7 (32-bit Pi) — target **arm64** only

---

## Exit criteria (Phase 6a)

- [x] `docker compose up -d --build` starts all services on ARM64
- [x] nginx proxies `/ws` for live dashboard in Docker
- [x] Production backend image (no dev pip extras)
- [x] README documents local build, Pi deploy, registry push/pull
- [x] `env.docker.example` + `docker-compose.pull.yml` committed
- [x] Docs: PHASE6 + ROADMAP updated
- [ ] Verified end-to-end on physical Raspberry Pi (operator checklist)

---

## Operational notes

### First run on Pi

```bash
git clone <repo> && cd dj
cp env.docker.example .env
# Edit .env — at minimum DJ_ACOUSTID_API_KEY
mkdir -p data/{watch,incoming,processing,ready,review,duplicates,archive,failed,logs,rekordbox}
docker compose up -d --build
```

Open `http://<pi-ip>:5173`. Drop audio into `data/watch/` (or your mounted sync path).

### Publish images (optional)

Build and push from a machine with `buildx`:

```bash
docker buildx build --platform linux/arm64 -f docker/Dockerfile.backend \
  -t YOUR_REGISTRY/dj-pipeline-backend:latest --push .
docker buildx build --platform linux/arm64 -f docker/Dockerfile.frontend \
  -t YOUR_REGISTRY/dj-pipeline-frontend:latest --push .
```

On the Pi, use `docker-compose.pull.yml` with `DJ_BACKEND_IMAGE` / `DJ_FRONTEND_IMAGE` — see README.

### Upgrade

```bash
docker compose pull   # if using registry images
docker compose up -d --build
```

SQLite and `data/` persist on the host volume.

---

## References

- [README.md](../README.md) — Docker quick start
- [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md) — Docker-first architecture
- [ROADMAP.md](./ROADMAP.md)
