#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> DJ Library Pipeline — development install"

command -v python3 >/dev/null || { echo "python3 required"; exit 1; }
command -v node >/dev/null || { echo "node required"; exit 1; }
command -v npm >/dev/null || { echo "npm required"; exit 1; }

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

python3 scripts/install.py

echo "==> Done. Run backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "==> Run frontend: cd frontend && npm run dev"
