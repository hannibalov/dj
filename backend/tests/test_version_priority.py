from pathlib import Path

from app.fingerprint.version_priority import preferred_track_ids
from app.models.track import Track


def _track(track_id: int, path: Path) -> Track:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"audio")
    return Track(id=track_id, source_path=str(path), processing_path=str(path))


def test_flac_and_mp3_both_preferred(tmp_path: Path) -> None:
    flac = _track(1, tmp_path / "a.flac")
    mp3 = _track(2, tmp_path / "a.mp3")
    assert preferred_track_ids([flac, mp3]) == {1, 2}


def test_higher_bitrate_mp3_preferred(tmp_path: Path) -> None:
    from unittest.mock import patch

    from app.utils.audio_format import StreamInfo

    low = _track(1, tmp_path / "low.mp3")
    high = _track(2, tmp_path / "high.mp3")

    def fake_stream(path: Path) -> StreamInfo:
        if path.name == "low.mp3":
            return StreamInfo(bitrate_kbps=128, sample_rate_hz=44100, bits_per_sample=None)
        if path.name == "high.mp3":
            return StreamInfo(bitrate_kbps=320, sample_rate_hz=44100, bits_per_sample=None)
        return StreamInfo(None, None, None)

    with patch("app.utils.audio_format._read_stream_info", side_effect=fake_stream):
        assert preferred_track_ids([low, high]) == {2}


def test_flac_preferred_over_mp3_in_same_family_not_applicable(tmp_path: Path) -> None:
    flac = _track(1, tmp_path / "song.flac")
    wav = _track(2, tmp_path / "song.wav")
    assert preferred_track_ids([flac, wav]) == {1}
