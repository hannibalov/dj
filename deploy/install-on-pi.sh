#!/bin/sh
# Download compose + env template and create data folders (no git clone).
set -eu

INSTALL_DIR="${1:-$HOME/dj-pipeline}"
REPO="${DJ_DEPLOY_REPO:-hannibalov/dj}"
BRANCH="${DJ_DEPLOY_BRANCH:-main}"
BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}/deploy"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "Downloading deploy files to $INSTALL_DIR ..."
curl -fsSL "$BASE/docker-compose.yml" -o docker-compose.yml
curl -fsSL "$BASE/.env.example" -o .env.example

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — edit DJ_ACOUSTID_API_KEY before starting."
fi

mkdir -p data/watch data/incoming data/processing data/ready data/review \
  data/duplicates data/archive data/failed data/logs data/rekordbox

echo ""
echo "Next:"
echo "  1. nano $INSTALL_DIR/.env"
echo "  2. cd $INSTALL_DIR && docker compose pull && docker compose up -d"
echo "  3. Open http://$(hostname -I 2>/dev/null | awk '{print $1}'):5173"
