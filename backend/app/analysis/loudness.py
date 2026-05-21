import re
import subprocess
from pathlib import Path

from app.logging import get_logger

logger = get_logger("ANALYZER")

_INTEGRATED_RE = re.compile(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS")
_PEAK_RE = re.compile(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS")


def measure_loudness(
    audio_path: Path,
    *,
    timeout_seconds: int = 300,
) -> tuple[float | None, float | None]:
    """Return integrated LUFS and true peak (dBFS) via ffmpeg ebur128."""
    if not audio_path.is_file():
        return None, None

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(audio_path),
        "-af",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("loudness_ffmpeg_failed", path=str(audio_path), error=str(exc))
        return None, None

    output = proc.stderr + proc.stdout
    integrated = _parse_integrated_lufs(output)
    peak = _parse_last(_PEAK_RE, output)
    if proc.returncode != 0 and integrated is None:
        logger.warning(
            "loudness_ffmpeg_error",
            path=str(audio_path),
            returncode=proc.returncode,
        )
    return integrated, peak


def _parse_integrated_lufs(text: str) -> float | None:
    """Prefer the final Summary block; fall back to the last progress-line I: value."""
    summary_start = text.rfind("Summary:")
    if summary_start >= 0:
        value = _parse_last(_INTEGRATED_RE, text[summary_start:])
        if value is not None:
            return value
    return _parse_last(_INTEGRATED_RE, text)


def _parse_last(pattern: re.Pattern[str], text: str) -> float | None:
    value: float | None = None
    for match in pattern.finditer(text):
        value = float(match.group(1))
    return value
