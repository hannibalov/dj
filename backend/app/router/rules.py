from pathlib import Path

from app.utils.audio_format import AudioFormatInfo, get_format_info


def needs_review(
    *,
    integrated_lufs: float | None,
    true_peak_db: float | None,
    lufs_threshold: float,
    peak_threshold: float,
) -> bool:
    """True when track is too quiet or peak exceeds the configured threshold."""
    too_quiet = integrated_lufs is not None and integrated_lufs < lufs_threshold
    clipped = true_peak_db is not None and true_peak_db > peak_threshold
    return too_quiet or clipped


def needs_quality_review(
    info: AudioFormatInfo,
    *,
    min_mp3_bitrate_kbps: int,
    min_lossless_bit_depth: int,
    min_lossless_sample_rate_hz: int,
) -> bool:
    """True when audio format is below configured minimum quality."""
    if (
        min_mp3_bitrate_kbps <= 0
        and min_lossless_bit_depth <= 0
        and min_lossless_sample_rate_hz <= 0
    ):
        return False
    if info.family == "mp3":
        if min_mp3_bitrate_kbps <= 0:
            return False
        if info.bitrate_kbps is None:
            return False
        return info.bitrate_kbps < min_mp3_bitrate_kbps
    if info.family == "lossless":
        if (
            min_lossless_bit_depth > 0
            and info.bits_per_sample is not None
            and info.bits_per_sample < min_lossless_bit_depth
        ):
            return True
        if (
            min_lossless_sample_rate_hz > 0
            and info.sample_rate_hz is not None
            and info.sample_rate_hz < min_lossless_sample_rate_hz
        ):
            return True
    return False


def needs_quality_review_for_path(
    path: Path,
    *,
    min_mp3_bitrate_kbps: int,
    min_lossless_bit_depth: int,
    min_lossless_sample_rate_hz: int,
) -> bool:
    return needs_quality_review(
        get_format_info(path),
        min_mp3_bitrate_kbps=min_mp3_bitrate_kbps,
        min_lossless_bit_depth=min_lossless_bit_depth,
        min_lossless_sample_rate_hz=min_lossless_sample_rate_hz,
    )
