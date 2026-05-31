#!/usr/bin/env python3
"""Development environment installer.

Sets up Python venv, npm deps, data folders, SQLite, and .env.
Does NOT install system audio tools — install separately before running the worker:
  ffmpeg (required), fpcalc/chromaprint (required), yt-dlp (required for YouTube downloads), Essentia (optional).
See README.md § System dependencies.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DATA = ROOT / "data"


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True, env=env)


def write_local_env(env_path: Path) -> None:
    """Write .env with absolute paths for local development."""
    folders = (
        "watch",
        "incoming",
        "processing",
        "ready",
        "review",
        "duplicates",
        "archive",
        "failed",
        "logs",
        "rekordbox",
    )
    lines = [
        "# Generated for local development by install.py",
        "# Docker overrides these via docker-compose.yml environment:",
        "",
        "DJ_ENV=development",
        "DJ_LOG_LEVEL=INFO",
        f"DJ_DATABASE_URL=sqlite:///{DATA / 'dj_library.db'}",
        "",
    ]
    folder_env_keys = {
        "watch": "DJ_WATCH_FOLDER",
        "incoming": "DJ_INCOMING_FOLDER",
        "processing": "DJ_PROCESSING_FOLDER",
        "ready": "DJ_READY_FOLDER",
        "review": "DJ_REVIEW_FOLDER",
        "duplicates": "DJ_DUPLICATES_FOLDER",
        "archive": "DJ_ARCHIVE_FOLDER",
        "failed": "DJ_FAILED_FOLDER",
        "logs": "DJ_LOGS_FOLDER",
        "rekordbox": "DJ_REKORDBOX_EXPORT_FOLDER",
    }
    for name in folders:
        lines.append(f"{folder_env_keys[name]}={DATA / name}")
    lines.extend(
        [
            "",
        "DJ_API_HOST=0.0.0.0",
        "DJ_API_PORT=8000",
        "DJ_API_INTERNAL_URL=http://127.0.0.1:8000",
            "DJ_WORKER_CPU_LIMIT=1.0",
            "DJ_WORKER_MEM_LIMIT=1g",
            "",
        ]
    )
    env_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote local paths to {env_path}")


def main() -> int:
    print("==> Validating tools")
    for tool in ("python3", "node", "npm"):
        if shutil.which(tool) is None:
            print(f"Missing required tool: {tool}", file=sys.stderr)
            return 1

    print("==> Creating runtime folders")
    for name in (
        "watch",
        "incoming",
        "processing",
        "ready",
        "review",
        "duplicates",
        "archive",
        "failed",
        "logs",
        "rekordbox",
    ):
        (DATA / name).mkdir(parents=True, exist_ok=True)

    print("==> Configure .env for local development")
    write_local_env(ROOT / ".env")

    print("==> Backend virtualenv")
    venv = BACKEND / ".venv"
    if not venv.exists():
        run([sys.executable, "-m", "venv", str(venv)])
    pip = venv / "bin" / "pip"
    run([str(pip), "install", "-e", ".[dev]"], cwd=BACKEND)

    print("==> Initialize database")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    env["DJ_DATABASE_URL"] = f"sqlite:///{DATA / 'dj_library.db'}"
    python = venv / "bin" / "python"
    subprocess.run(
        [str(python), "-m", "app.db.init_db"],
        cwd=BACKEND,
        check=True,
        env=env,
    )

    print("==> Frontend dependencies")
    run(["npm", "install"], cwd=FRONTEND)

    print("==> Install complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
