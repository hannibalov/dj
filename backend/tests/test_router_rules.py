from app.router.rules import needs_quality_review, needs_review
from app.utils.audio_format import AudioFormatInfo


def test_needs_review_when_too_quiet() -> None:
    assert needs_review(
        integrated_lufs=-20.0,
        true_peak_db=-2.0,
        lufs_threshold=-18.0,
        peak_threshold=-0.1,
    )


def test_needs_review_when_peak_too_high() -> None:
    assert needs_review(
        integrated_lufs=-14.0,
        true_peak_db=4.0,
        lufs_threshold=-18.0,
        peak_threshold=3.0,
    )


def test_passes_when_within_limits() -> None:
    assert not needs_review(
        integrated_lufs=-14.0,
        true_peak_db=-1.0,
        lufs_threshold=-18.0,
        peak_threshold=3.0,
    )


def test_passes_typical_mp3_inter_sample_peak() -> None:
    assert not needs_review(
        integrated_lufs=-8.6,
        true_peak_db=1.5,
        lufs_threshold=-18.0,
        peak_threshold=3.0,
    )


def test_quality_review_when_mp3_below_threshold() -> None:
    info = AudioFormatInfo(
        extension=".mp3",
        family="mp3",
        format_rank=3,
        bitrate_kbps=128,
    )
    assert needs_quality_review(
        info,
        min_mp3_bitrate_kbps=320,
        min_lossless_bit_depth=16,
        min_lossless_sample_rate_hz=44100,
    )


def test_quality_passes_when_mp3_meets_threshold() -> None:
    info = AudioFormatInfo(
        extension=".mp3",
        family="mp3",
        format_rank=3,
        bitrate_kbps=320,
    )
    assert not needs_quality_review(
        info,
        min_mp3_bitrate_kbps=320,
        min_lossless_bit_depth=16,
        min_lossless_sample_rate_hz=44100,
    )


def test_quality_review_when_lossless_below_bit_depth() -> None:
    info = AudioFormatInfo(
        extension=".wav",
        family="lossless",
        format_rank=1,
        bitrate_kbps=None,
        sample_rate_hz=48000,
        bits_per_sample=16,
    )
    assert needs_quality_review(
        info,
        min_mp3_bitrate_kbps=320,
        min_lossless_bit_depth=24,
        min_lossless_sample_rate_hz=44100,
    )


def test_quality_gate_disabled_when_zero() -> None:
    info = AudioFormatInfo(
        extension=".mp3",
        family="mp3",
        format_rank=3,
        bitrate_kbps=64,
    )
    assert not needs_quality_review(
        info,
        min_mp3_bitrate_kbps=0,
        min_lossless_bit_depth=0,
        min_lossless_sample_rate_hz=0,
    )
