"""Chromaprint fingerprinting via fpcalc."""

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FingerprintData:
    fingerprint_hash: str
    duration_seconds: float | None
    raw_fingerprint: str


class FingerprintError(Exception):
    pass


def compute_fingerprint(path: Path) -> FingerprintData:
    if not path.is_file():
        raise FingerprintError(f"Audio file not found: {path}")

    try:
        proc = subprocess.run(
            ["fpcalc", "-json", str(path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise FingerprintError("fpcalc not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise FingerprintError(stderr or f"fpcalc failed with code {exc.returncode}") from exc

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise FingerprintError("Invalid fpcalc JSON output") from exc

    raw = payload.get("fingerprint")
    if not raw:
        raise FingerprintError("fpcalc returned no fingerprint")

    duration = payload.get("duration")
    duration_seconds = float(duration) if duration is not None else None
    fingerprint_hash = hashlib.sha256(str(raw).encode()).hexdigest()

    return FingerprintData(
        fingerprint_hash=fingerprint_hash,
        duration_seconds=duration_seconds,
        raw_fingerprint=str(raw),
    )
