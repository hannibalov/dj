# Docker Hub — publish from Mac, run on Pi

## Do you build locally?

**Yes — once per release**, on your Mac (with the full repo). Docker Hub does not build images automatically just because the GitHub repo exists.

1. **Mac:** `docker login` → build → `docker push` (script below).
2. **Pi:** `docker pull` → `docker compose up` (no repo clone).

You only need the small `deploy/docker-compose.yml` on the Pi so Docker knows how to run all five containers together.

---

## 1. Publish from your Mac

Clone or open the repo on your Mac (you already have it for development):

```bash
cd /path/to/dj
docker login    # Docker Hub username + password / access token
chmod +x deploy/publish-dockerhub.sh
./deploy/publish-dockerhub.sh
```

Default image names (change `DOCKER_USER` if your Hub username is not `hannibalov`):

| Image | Pull on Pi |
|-------|------------|
| `hannibalov/dj-pipeline-backend:latest` | `docker pull hannibalov/dj-pipeline-backend:latest` |
| `hannibalov/dj-pipeline-frontend:latest` | `docker pull hannibalov/dj-pipeline-frontend:latest` |

**Apple Silicon Mac:** builds `linux/arm64` natively for the Pi.

**Intel Mac:** same script; buildx cross-builds arm64.

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
printf 'DJ_ENV=production\nDJ_ACOUSTID_API_KEY=your_key\n' > .env

mkdir -p data/{watch,incoming,processing,ready,review,duplicates,archive,failed,logs,rekordbox}

docker compose pull
docker compose up -d
```

Open **http://\<pi-ip\>:5173**

If your Docker Hub username is not `hannibalov`, add to `.env`:

```env
DJ_BACKEND_IMAGE=youruser/dj-pipeline-backend:latest
DJ_FRONTEND_IMAGE=youruser/dj-pipeline-frontend:latest
```

### Mount a sync folder as watch

Edit `docker-compose.yml` under `api`, `worker`, and `watcher`:

```yaml
    volumes:
      - ./data:/data
      - /home/pi/nextcloud/Music/Inbox:/data/watch
```

### Upgrade after you push a new image from the Mac

```bash
cd ~/dj-pipeline
docker compose pull && docker compose up -d
```

---

## FAQ

**Does pushing to GitHub publish Docker Hub images?**  
No. Only `docker push` after a local (or CI) build does.

**Why not only `docker pull` one image?**  
The app is five services (API, worker, watcher, scheduler, UI). Compose wires them; each service has its own image (backend vs frontend).

**Private images on Docker Hub?**  
Run `docker login` on the Pi before `docker compose pull`.
