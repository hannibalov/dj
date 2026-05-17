"""Audio container/format helpers for duplicate version priority."""

from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile  # type: ignore[attr-defined]

LOSSLESS_EXTENSIONS = frozenset({".flac", ".wav", ".aiff", ".aif"})
MP3_EXTENSION = ".mp3"

# Lower rank = higher priority (spec: FLAC → WAV → AIFF → 320k MP3 → lower MP3).
FORMAT_RANK = {
    ".flac": 0,
    ".wav": 1,
    ".aiff": 2,
    ".aif": 2,
    ".mp3": 3,
}


@dataclass(frozen=True)
class AudioFormatInfo:
    extension: str
    family: str
    format_rank: int
    bitrate_kbps: int | None


def get_format_info(path: Path) -> AudioFormatInfo:
    ext = path.suffix.lower()
    family = _format_family(ext)
    bitrate = _read_bitrate_kbps(path) if ext == MP3_EXTENSION else None
    rank = FORMAT_RANK.get(ext, 99)
    return AudioFormatInfo(
        extension=ext,
        family=family,
        format_rank=rank,
        bitrate_kbps=bitrate,
    )


def format_priority(info: AudioFormatInfo) -> tuple[int, int]:
    """Sort key: lower is better. MP3 ties break on higher bitrate."""
    bitrate = info.bitrate_kbps if info.bitrate_kbps is not None else 0
    return (info.format_rank, -bitrate)


def _format_family(ext: str) -> str:
    if ext in LOSSLESS_EXTENSIONS:
        return "lossless"
    if ext == MP3_EXTENSION:
        return "mp3"
    return "other"


def _read_bitrate_kbps(path: Path) -> int | None:
    try:
        audio = MutagenFile(path)
    except Exception:
        return None
    if audio is None or not hasattr(audio, "info") or audio.info is None:
        return None
    bitrate = getattr(audio.info, "bitrate", None)
    if bitrate is None:
        return None
    return int(bitrate // 1000)
