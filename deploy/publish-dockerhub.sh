#!/usr/bin/env bash
# Build on your Mac and push to Docker Hub (run from repo root).
#
#   docker login
#   ./deploy/publish-dockerhub.sh
#
# Override Docker Hub username if needed:
#   DOCKER_USER=myuser ./deploy/publish-dockerhub.sh
#
# Pi needs arm64; Intel Macs use buildx (installed with Docker Desktop).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER_USER="${DOCKER_USER:-hannibalov}"
TAG="${TAG:-latest}"
PLATFORMS="${PLATFORMS:-linux/arm64}"

BACKEND="${DOCKER_USER}/dj-pipeline-backend:${TAG}"
FRONTEND="${DOCKER_USER}/dj-pipeline-frontend:${TAG}"

cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop and try again."
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
echo "Set in ~/dj-pipeline/.env if your Docker Hub user is not ${DOCKER_USER}:"
echo "  DJ_BACKEND_IMAGE=${BACKEND}"
echo "  DJ_FRONTEND_IMAGE=${FRONTEND}"
