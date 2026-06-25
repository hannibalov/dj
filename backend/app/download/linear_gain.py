"""Apply uniform (linear) gain from measured integrated LUFS — no dynamic compression."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.analysis.loudness import measure_loudness
from app.logging import get_logger

logger = get_logger("ROUTER")

# Club playback target: boost quiet sources toward this level without reshaping dynamics.
CLUB_TARGET_LUFS = -9.0
CLUB_PEAK_CEILING_DB = -0.5
OUTPUT_SAMPLE_RATE_HZ = 44100
MP3_BITRATE = "320k"

_MIN_APPLY_GAIN_DB = 0.05


class LinearGainError(Exception):
    pass


@dataclass(frozen=True)
class LinearGainResult:
    gain_db: float
    measured_lufs: float | None
    measured_peak_db: float | None
    applied: bool


def compute_linear_gain_db(
    measured_lufs: float | None,
    measured_peak_db: float | None,
    *,
    target_lufs: float = CLUB_TARGET_LUFS,
    peak_ceiling_db: float = CLUB_PEAK_CEILING_DB,
) -> float:
    """Return a single dB offset applied equally to every sample.

    Never attenuates (gain >= 0). Caps boost so true peak stays at or below peak_ceiling_db.
    """
    if measured_lufs is None:
        return 0.0

    gain_for_lufs = target_lufs - measured_lufs
    if gain_for_lufs <= 0:
        return 0.0

    gain_db = gain_for_lufs
    if measured_peak_db is not None:
        headroom_db = peak_ceiling_db - measured_peak_db
        gain_db = min(gain_for_lufs, headroom_db)

    return max(0.0, gain_db)


def apply_linear_gain(
    audio_path: Path,
    *,
    target_lufs: float = CLUB_TARGET_LUFS,
    peak_ceiling_db: float = CLUB_PEAK_CEILING_DB,
    timeout_seconds: int = 600,
) -> LinearGainResult:
    """Measure LUFS, then apply uniform ``volume`` gain in-place when needed."""
    if not audio_path.is_file():
        raise LinearGainError(f"Audio file not found: {audio_path}")

    measured_lufs, measured_peak = measure_loudness(audio_path, timeout_seconds=timeout_seconds)
    gain_db = compute_linear_gain_db(
        measured_lufs,
        measured_peak,
        target_lufs=target_lufs,
        peak_ceiling_db=peak_ceiling_db,
    )

    if gain_db < _MIN_APPLY_GAIN_DB:
        logger.info(
            "linear_gain_skipped",
            path=str(audio_path),
            measured_lufs=measured_lufs,
            measured_peak_db=measured_peak,
            gain_db=gain_db,
        )
        return LinearGainResult(
            gain_db=gain_db,
            measured_lufs=measured_lufs,
            measured_peak_db=measured_peak,
            applied=False,
        )

    with tempfile.NamedTemporaryFile(
        suffix=audio_path.suffix,
        dir=audio_path.parent,
        delete=False,
    ) as tmp:
        temp_path = Path(tmp.name)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(audio_path),
        "-af",
        f"volume={gain_db:.4f}dB",
        "-ar",
        str(OUTPUT_SAMPLE_RATE_HZ),
        "-c:a",
        "libmp3lame",
        "-b:a",
        MP3_BITRATE,
        "-map_metadata",
        "0",
        str(temp_path),
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
        temp_path.unlink(missing_ok=True)
        raise LinearGainError(f"ffmpeg gain failed: {exc}") from exc

    if proc.returncode != 0:
        temp_path.unlink(missing_ok=True)
        stderr = (proc.stderr or "").strip()
        raise LinearGainError(stderr or f"ffmpeg exited {proc.returncode}")

    temp_path.replace(audio_path)
    logger.info(
        "linear_gain_applied",
        path=str(audio_path),
        measured_lufs=measured_lufs,
        measured_peak_db=measured_peak,
        gain_db=gain_db,
    )
    return LinearGainResult(
        gain_db=gain_db,
        measured_lufs=measured_lufs,
        measured_peak_db=measured_peak,
        applied=True,
    )
