import struct
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.enums import TrackStatus
from app.models.track import Track
from app.services.track_service import TrackService
from app.utils.audio_format import get_format_info


def _minimal_wav(path: Path) -> None:
    data = b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt " + struct.pack("<I", 16)
    data += struct.pack("<HHIIHH", 1, 1, 48000, 96000, 2, 24)
    data += b"data" + struct.pack("<I", 0)
    path.write_bytes(data)


def test_track_response_includes_format_from_processing_file(
    db_session,
    tmp_path: Path,
) -> None:
    wav = tmp_path / "artist - title.wav"
    _minimal_wav(wav)
    track = Track(
        source_path=str(tmp_path / "watch" / wav.name),
        processing_path=str(wav),
        status=TrackStatus.INGESTED,
    )
    db_session.add(track)
    db_session.commit()

    response = TrackService(db_session).get_track(track.id)

    assert response is not None
    assert response.format_extension == ".wav"
    assert response.audio_family == "lossless"
    assert response.sample_rate_hz == 48000
    assert response.bits_per_sample == 24
    assert response.bitrate_kbps is None


def test_track_response_mp3_bitrate(db_session, tmp_path: Path) -> None:
    mp3 = tmp_path / "song.mp3"
    mp3.write_bytes(b"fake")
    track = Track(
        source_path=str(mp3),
        processing_path=str(mp3),
        status=TrackStatus.INGESTED,
    )
    db_session.add(track)
    db_session.commit()

    with patch("app.utils.audio_format._read_stream_info") as mock_stream:
        from app.utils.audio_format import StreamInfo

        mock_stream.return_value = StreamInfo(
            bitrate_kbps=320,
            sample_rate_hz=44100,
            bits_per_sample=None,
        )
        response = TrackService(db_session).get_track(track.id)

    assert response is not None
    assert response.format_extension == ".mp3"
    assert response.audio_family == "mp3"
    assert response.bitrate_kbps == 320


def test_get_format_info_reads_real_mp3_bitrates(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    samples = list(repo_root.rglob("Wonderwall - Oasis.mp3"))
    if not samples:
        pytest.skip("sample mp3 not in repo")
    info = get_format_info(samples[0])
    assert info.family == "mp3"
    assert info.bitrate_kbps == 128

    samples_320 = [
        p
        for p in repo_root.rglob("*.mp3")
        if "Jan Blomqvist" in p.name and p.stat().st_size > 5000
    ]
    if samples_320:
        info_320 = get_format_info(samples_320[0])
        assert info_320.bitrate_kbps == 320
