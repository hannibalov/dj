# Docker Hub — publish from Mac, run on Pi

## Do you build locally?

**Yes — once per release**, on your Mac (with the full repo). Docker Hub does not build images automatically just because the GitHub repo exists.

1. **Mac:** `docker login` → build → `docker push` (script below).
2. **Pi:** `docker pull` → `docker compose up` (no repo clone).

You only need the small `deploy/docker-compose.yml` on the Pi so Docker knows how to run all five containers together.

### Which compose file is which?

| File | Use on |
|------|--------|
| **`deploy/docker-compose.yml`** (this folder) | **Pi / production** — `docker compose pull` using `DOCKER_USER` from `.env` |
| **`docker-compose.yml`** (repo root) | **Mac / dev** — `docker compose up -d --build` from a git clone |
| **`docker-compose.pull.yml`** (repo root) | **Deprecated** — old GHCR-style `DJ_BACKEND_IMAGE` variables; use `deploy/` instead |

Do not copy both compose files to the Pi; only **`deploy/docker-compose.yml`**.

---

## 1. Publish from your Mac

Clone or open the repo on your Mac (you already have it for development):

```bash
cd /path/to/dj
docker login -u YOUR_DOCKERHUB_USERNAME   # use your Hub ID, not GitHub username
chmod +x deploy/publish-dockerhub.sh
DOCKER_USER=YOUR_DOCKERHUB_USERNAME ./deploy/publish-dockerhub.sh
```

Image names use **your Docker Hub ID** (see https://hub.docker.com/settings/general):

| Image | Example |
|-------|---------|
| `YOUR_USER/dj-pipeline-backend:latest` | `docker pull YOUR_USER/dj-pipeline-backend:latest` |
| `YOUR_USER/dj-pipeline-frontend:latest` | `docker pull YOUR_USER/dj-pipeline-frontend:latest` |

**Push denied?** The script was probably pushing to the wrong namespace (e.g. `hannibalov/...` while you are logged in as someone else). Always set `DOCKER_USER` to the account you used for `docker login`.

**Apple Silicon Mac:** builds `linux/arm64` natively for the Pi.

**Intel Mac:** same script; buildx cross-builds arm64.

**First backend build** compiles Essentia from source (~5–15 minutes depending on CPU). Later builds cache that layer. The image includes BPM/key analysis (no separate install on the Pi).

To also publish amd64 (optional):

```bash
PLATFORMS=linux/arm64,linux/amd64 ./deploy/publish-dockerhub.sh
```

Manual equivalent (no script):

```bash
docker buildx build --platform linux/arm64 -f docker/Dockerfile.backend \
  -t hannibalov/dj-pipeline-backend:latest --push .
docker buildx build --platform linux/arm64 -f docker/Dockerfile.frontend \
  -t hannibalov/dj-pipeline-frontend:latest --push .
```

---

## 2. Run on the Raspberry Pi

No git clone. Only Docker + compose file + `.env`.

```bash
mkdir -p ~/dj-pipeline && cd ~/dj-pipeline

curl -fsSLO https://raw.githubusercontent.com/hannibalov/dj/main/deploy/docker-compose.yml
printf 'DOCKER_USER=youruser\nDJ_ENV=production\nDJ_ACOUSTID_API_KEY=your_key\n' > .env

mkdir -p data/{watch,incoming,processing,ready,review,duplicates,archive,failed,logs,rekordbox}

docker compose pull
docker compose up -d
```

Open **http://\<pi-ip\>:5173**

Your `.env` must include `DOCKER_USER` (your Docker Hub ID — same as on the Mac):

```env
DOCKER_USER=youruser
DJ_ACOUSTID_API_KEY=your_key
```

### Mount a sync folder as watch

Edit `docker-compose.yml` under `api`, `worker`, and `watcher`:

```yaml
    volumes:
      - ./data:/data
      - /home/pi/nextcloud/Music/Inbox:/data/watch
```

### Volume permissions on the Pi

If you run `docker compose` with `sudo`, the host `data/` directories and files can end up owned by `root:root`. That is why adding `user: "33:33"` inside the compose file can make the container fail: the container process runs as `www-data` and needs a writable host volume.

Before starting the stack, make sure the data tree is owned by the same UID/GID and has group write permissions:

```bash
sudo chown -R 33:33 data
find data -type d -exec chmod 775 {} +
find data -type f -exec chmod 664 {} +
```

If you mount an external folder into `/data/watch`, make sure the host mount also allows access for UID/GID `33:33`.

Avoid using `user: "33:33"` unless the mounted host directories are already compatible with that UID/GID. If `./data` is root-owned and not group-writable, a `www-data` container user may be unable to open or create files.

### Upgrade after you push a new image from the Mac

```bash
cd ~/dj-pipeline
docker compose pull && docker compose up -d
```

Open the dashboard → **Genre backfill** to fetch missing genre/subgenre for already-tagged tracks (inline MusicBrainz lookup; no worker queue). Use **Reanalyze all** if a release fixed analysis, tagging, WAV support, or you need a full pipeline refresh — the **worker** must be running until the job queue is empty.

After upgrading, it is normal to see **Backlogged** with many pending jobs on a Pi — the worker runs **one job at a time** (analyze: ffmpeg loudness + Essentia BPM/key is slow). Pipeline chips show granular steps (**Awaiting analyze**, **Analyzed**, **Awaiting tag**, …); artist/title and genre/subgenre fill in at **TAG**, not during analyze.

If you accumulated **failed jobs** from an older image (e.g. WAV `not a Frame instance` on tag rows), use **Clear failed jobs** after deploying the fix, then **Reanalyze all** (or per-track **Reset**). Clearing failed jobs alone does not re-queue tracks. See [Dashboard troubleshooting](#dashboard-troubleshooting-pi) and [README § Dashboard](../README.md#dashboard).

**Example** (images published as `rodriguescu`):

```bash
docker pull rodriguescu/dj-pipeline-backend:latest
docker pull rodriguescu/dj-pipeline-frontend:latest
```

---


## Resource limits on the Pi (CPU / memory)

`deploy/docker-compose.yml` sets `cpus` and `mem_limit` per service. If you see:

```text
Your kernel does not support memory limit capabilities or the cgroup is not mounted.
```

those limits are **not enforced** — containers can use all free RAM/CPU on the Pi until you fix cgroups or use another method below.

### Option A — Enable cgroups (recommended; makes Compose limits work)

On **Raspberry Pi OS**, edit the kernel cmdline (path may be `/boot/firmware/cmdline.txt` or `/boot/cmdline.txt`). On the **same line** as the existing options, add a space and:

```text
cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1
```

Reboot, then check:

```bash
grep memory /proc/cgroup   # or: cat /sys/fs/cgroup/cgroup.controllers  (cgroup v2)
sudo docker compose up -d
```

Re-create containers so limits apply: `docker compose up -d --force-recreate`.

If limits still fail, ensure Docker uses the cgroup driver expected by your OS (`docker info | grep -i cgroup`). On Bookworm, Docker usually works after the cmdline change above.

### Option B — Operational (no kernel change)

| Approach | Effect |
|----------|--------|
| **Stop the worker when idle** | `docker compose stop worker` — pipeline pauses; watcher/API stay up. Start again: `docker compose start worker`. |
| **Scale worker to zero** | `docker compose up -d --scale worker=0` (not in default compose; use `stop` instead). |
| **Process in batches** | Drop a few files in watch, wait for jobs to finish, then add more — only one analyze/ffmpeg job runs at a time in the worker. |
| **Lower ffmpeg load** | Heavy step is analyze (ffmpeg). Fewer simultaneous files = less spike load. |

The worker already runs **one job at a time**; the main risk is a single ffmpeg/ANALYZE pass using a full CPU core and ~200–500 MB RAM.

### Option C — Host tools (limits without Docker cgroups)

**systemd** — run only the worker under a resource cap (example unit fragment):

```ini
[Service]
CPUQuota=50%
MemoryMax=512M
```

**nice** — lower priority so other Pi services win (soft limit, not a hard cap). In `docker-compose.yml` override:

```yaml
  worker:
    command: ["nice", "-n", "15", "python", "-m", "app.workers.main"]
```

**cpulimit** — install on the Pi and wrap the worker PID (fragile across restarts; usually not worth it with Compose).

### What uses resources?

| Service | Typical load |
|---------|----------------|
| **worker** | High during ANALYZE (ffmpeg); low otherwise |
| **api** | Low |
| **watcher** | Very low |
| **scheduler** | Very low |
| **frontend** | Low (nginx static + proxy) |

Tuning compose `mem_limit` / `cpus` is the cleanest approach once **Option A** is in place.

---

## Dashboard troubleshooting (Pi)

| Symptom | Likely cause | What to do |
|---------|----------------|------------|
| Many **Awaiting analyze**, no artist/title | TAG not reached yet (normal after **Reanalyze all**) or TAG failed | Wait for queue, or check **Recent jobs** for `tag` errors. Worker must be Up. |
| Tracks on **Awaiting tag** with artist/title but no genre | Filename-only match; empty embedded genre | **Genre backfill** after TAG, or **Approve** / **Reanalyze all** |
| TAG fails on **.wav** with `not a Frame instance` | Old image: WAV/AIFF tags need ID3 frames | Pull latest backend image; **Reanalyze all** |
| **Worker idle** but 0 pending, tracks not **Ready** | Queue empty; tracks stuck after earlier failures | **Reanalyze all** or per-track **Reset**; then **Clear failed jobs** |
| **Analyze backlog** does nothing | Only enqueues tracks with no LUFS yet | Use **Reanalyze all** if BPM/LUFS already filled |
| **Worker idle**, many **pending** | Normal gap between jobs on Pi | Should show **Backlogged**; confirm `worker` is Up: `docker compose logs worker --tail 30` |
| **Stalled**, pending > 0, running = 0 | Worker stopped or jobs stuck `running` | `docker compose start worker` or **Retry stalled jobs** |
| No **genre** / **subgenre** | MB recording has no tags; empty embedded genre | **Genre backfill** (fast); edit inline in the tracks table; **Reanalyze all** for full refresh; ensure Pi can reach `musicbrainz.org` |
| Filename looks like title–artist reversed | Library template is `Title - Artist (Mix).ext` by design | Table artist/title are still correct; edit inline if needed |
| Pipeline shows **100** songs but you have more | Old image capped list at 100 | Upgrade image; chips use full DB counts on current builds |
| Many **failed jobs** | Historical failures | **Clear failed jobs** after deploying fixes (does not re-queue tracks) |

See also [README § Dashboard](../README.md#dashboard) for tracks-table columns (format, quality, bitrate, loudness badges, editable metadata) and [Settings page](../README.md#settings-page) for routing gates.

```bash
docker compose ps
docker compose logs worker --tail 50
```

---

## FAQ

**Does pushing to GitHub publish Docker Hub images?**  
No. Only `docker push` after a local (or CI) build does.

**Why not only `docker pull` one image?**  
The app is five services (API, worker, watcher, scheduler, UI). Compose wires them; each service has its own image (backend vs frontend).

**Private images on Docker Hub?**  
Run `docker login` on the Pi before `docker compose pull`.
