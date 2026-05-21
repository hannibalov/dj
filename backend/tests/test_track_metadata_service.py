import struct
from pathlib import Path
from unittest.mock import patch

import pytest
from mutagen.wave import WAVE

from app.models.enums import TrackStatus
from app.models.track import Track
from app.services.track_metadata_service import TrackMetadataError, TrackMetadataService


def _minimal_wav(path: Path) -> None:
    data = b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt " + struct.pack("<I", 16)
    data += struct.pack("<HHIIHH", 1, 1, 44100, 88200, 2, 16)
    data += b"data" + struct.pack("<I", 0)
    path.write_bytes(data)


def _settings(db_session, tmp_path: Path) -> None:
    from app.models.setting import Setting

    db_session.add(Setting(key="naming_template", value="{title} - {artist} ({mix}){ext}"))
    db_session.commit()


def test_update_metadata_writes_tags_and_db(db_session, tmp_path: Path) -> None:
    wav = tmp_path / "processing" / "wrong - name.wav"
    wav.parent.mkdir(parents=True)
    _minimal_wav(wav)
    track = Track(
        source_path=str(tmp_path / "watch" / wav.name),
        processing_path=str(wav),
        status=TrackStatus.REVIEW,
        needs_metadata_review=True,
    )
    db_session.add(track)
    db_session.commit()
    _settings(db_session, tmp_path)

    with patch("app.services.track_metadata_service.notify_pipeline_changed"):
        updated = TrackMetadataService(db_session).update_metadata(
            track.id,
            artist="deadmau5",
            title="Strobe",
        )

    assert updated.artist == "deadmau5"
    assert updated.title == "Strobe"
    assert updated.needs_metadata_review is False
    assert updated.tag_confidence == 1.0
    assert updated.tagged_at is not None

    tagged = WAVE(updated.processing_path)
    assert str(tagged.tags["TPE1"]) == "deadmau5"
    assert str(tagged.tags["TIT2"]) == "Strobe"
    assert "Strobe - deadmau5" in Path(updated.processing_path).name


def test_update_metadata_requires_audio_file(db_session) -> None:
    track = Track(source_path="/missing/file.wav", status=TrackStatus.INGESTED)
    db_session.add(track)
    db_session.commit()

    with pytest.raises(TrackMetadataError, match="No audio file"):
        TrackMetadataService(db_session).update_metadata(
            track.id,
            artist="A",
            title="B",
        )
