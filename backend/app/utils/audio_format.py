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
class StreamInfo:
    bitrate_kbps: int | None
    sample_rate_hz: int | None
    bits_per_sample: int | None


@dataclass(frozen=True)
class AudioFormatInfo:
    extension: str
    family: str
    format_rank: int
    bitrate_kbps: int | None
    sample_rate_hz: int | None = None
    bits_per_sample: int | None = None


def get_format_info(path: Path) -> AudioFormatInfo:
    ext = path.suffix.lower()
    family = _format_family(ext)
    stream = _read_stream_info(path)
    rank = FORMAT_RANK.get(ext, 99)
    bitrate = stream.bitrate_kbps if ext == MP3_EXTENSION else None
    return AudioFormatInfo(
        extension=ext,
        family=family,
        format_rank=rank,
        bitrate_kbps=bitrate,
        sample_rate_hz=stream.sample_rate_hz,
        bits_per_sample=stream.bits_per_sample,
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


def _read_stream_info(path: Path) -> StreamInfo:
    try:
        audio = MutagenFile(path)
    except Exception:
        return StreamInfo(None, None, None)
    if audio is None or not hasattr(audio, "info") or audio.info is None:
        return StreamInfo(None, None, None)
    info = audio.info
    bitrate = getattr(info, "bitrate", None)
    bitrate_kbps = int(bitrate // 1000) if bitrate else None
    sample_rate = getattr(info, "sample_rate", None)
    bits_per_sample = getattr(info, "bits_per_sample", None)
    return StreamInfo(
        bitrate_kbps=bitrate_kbps,
        sample_rate_hz=int(sample_rate) if sample_rate else None,
        bits_per_sample=int(bits_per_sample) if bits_per_sample else None,
    )


def _read_bitrate_kbps(path: Path) -> int | None:
    return _read_stream_info(path).bitrate_kbps
