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
| **5d** | Loudness thresholds in Settings UI | Done — `LoudnessSettingsForm` + quality gates (`QualitySettingsForm`); env still sets defaults | — |
| **5d** | Duplicate rule toggle | User-configurable “FLAC + MP3 keep both” vs single keeper | 7c |

### Cross-phase / spec — still open

| Item | Source | Notes |
|------|--------|--------|
| ~~Essentia in Docker on ARM/Pi~~ | Phase 2, spec | Done — BPM/key in `docker/Dockerfile.backend` |
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
7c  Duplicate-rule settings UI (5d remainder)
7d  ~~Essentia on ARM~~ (done — BPM/key in backend image)
8+  Logs API, metrics dashboard, Picard/artwork
```

---

## Phase 6a — scope (minimum shippable)

### Delivered / in this milestone

| Area | Item |
|------|------|
| Images | `docker/Dockerfile.backend` (ffmpeg + fpcalc + Essentia BPM/key, production pip install) |
| Images | `docker/Dockerfile.frontend` (nginx static + API/WS proxy) |
| Compose | Root `docker-compose.yml` (build); `deploy/docker-compose.yml` (Pi pull via `DOCKER_USER`) |
| Networking | nginx proxies `/api` and `/ws` to API container |
| Deploy bundle | `deploy/` — compose + `.env.example` + `install-on-pi.sh` (curl, no clone) |
| CI | `.github/workflows/docker-publish.yml` → GHCR multi-arch |
| Docs | README + [deploy/README.md](../deploy/README.md) |

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
- ~~Essentia inside the image~~ — included in backend image
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

### Pi deploy (no git clone)

See **[deploy/README.md](../deploy/README.md)**.

```bash
curl -fsSL https://raw.githubusercontent.com/hannibalov/dj/main/deploy/install-on-pi.sh | sh
cd ~/dj-pipeline && nano .env
docker compose pull && docker compose up -d
```

Only `deploy/docker-compose.yml`, `.env`, and `data/` live on the Pi.

**Why two compose files?** Root `docker-compose.yml` is for developers who clone the repo and **build** locally. `deploy/docker-compose.yml` is for the Pi: it **pulls** `DOCKER_USER/dj-pipeline-*` images and needs no source tree. The legacy `docker-compose.pull.yml` (full `DJ_*_IMAGE` URLs) is deprecated.

### Publish images

- **Docker Hub (recommended for Pi):** `DOCKER_USER=yourhub ./deploy/publish-dockerhub.sh` on a Mac → Pi runs `docker compose pull`
- **CI (optional):** `.github/workflows/docker-publish.yml` → GHCR
- **Local:** `docker buildx` with `--platform linux/arm64 --push` (see [deploy/README.md](../deploy/README.md))

Set GHCR packages to **public** so the Pi can pull without `docker login`.

### Upgrade on Pi

```bash
cd ~/dj-pipeline
docker compose pull && docker compose up -d
```

---

## References

- [README.md](../README.md) — Docker quick start
- [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md) — Docker-first architecture
- [ROADMAP.md](./ROADMAP.md)
