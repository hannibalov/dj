#!/usr/bin/env bash
# Build on your Mac and push to Docker Hub (run from repo root).
#
#   docker login -u YOUR_DOCKERHUB_USERNAME
#   DOCKER_USER=YOUR_DOCKERHUB_USERNAME ./deploy/publish-dockerhub.sh
#
# Image tags must match the account you logged into (not the GitHub username).
#
# Pi needs arm64; Intel Macs use buildx (installed with Docker Desktop).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "${DOCKER_USER:-}" ]; then
  echo "Set your Docker Hub username (same account as 'docker login'):"
  echo "  DOCKER_USER=yourhubname ./deploy/publish-dockerhub.sh"
  echo ""
  echo "Check https://hub.docker.com/settings/general — 'Docker ID' is your username."
  exit 1
fi

TAG="${TAG:-latest}"
PLATFORMS="${PLATFORMS:-linux/arm64}"

BACKEND="${DOCKER_USER}/dj-pipeline-backend:${TAG}"
FRONTEND="${DOCKER_USER}/dj-pipeline-frontend:${TAG}"

cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop and try again."
  exit 1
fi

if ! grep -q 'index.docker.io\|docker.io' "${HOME}/.docker/config.json" 2>/dev/null; then
  echo "Not logged into Docker Hub. Run: docker login -u ${DOCKER_USER}"
  exit 1
fi

if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is required (Docker Desktop includes it)."
  exit 1
fi

docker buildx inspect dj-pipeline-builder >/dev/null 2>&1 \
  || docker buildx create --name dj-pipeline-builder --use
docker buildx use dj-pipeline-builder

echo "Publishing to Docker Hub as ${DOCKER_USER} (platforms: ${PLATFORMS})"
echo "  ${BACKEND}"
echo "  ${FRONTEND}"
echo ""

docker buildx build --platform "${PLATFORMS}" \
  -f docker/Dockerfile.backend \
  -t "${BACKEND}" \
  --push \
  .

docker buildx build --platform "${PLATFORMS}" \
  -f docker/Dockerfile.frontend \
  -t "${FRONTEND}" \
  --push \
  .

echo ""
echo "Done. On the Pi:"
echo "  docker pull ${BACKEND}"
echo "  docker pull ${FRONTEND}"
echo ""
echo "On the Pi, add to ~/dj-pipeline/.env:"
echo "  DOCKER_USER=${DOCKER_USER}"
