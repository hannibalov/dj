import struct
from pathlib import Path
from unittest.mock import patch

import pytest
from mutagen.wave import WAVE

from app.metadata.musicbrainz_lookup import RecordingGenreInfo
from app.models.enums import TrackStatus
from app.models.setting import Setting
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


def test_update_metadata_resolves_genres_after_edit(db_session, tmp_path: Path) -> None:
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

    with (
        patch("app.services.track_metadata_service.notify_pipeline_changed"),
        patch(
            "app.services.track_metadata_service.resolve_track_genres",
            return_value=RecordingGenreInfo("Techno", "Minimal Techno", "mbid-techno"),
        ),
        patch("app.services.track_metadata_service.apply_resolved_genres_to_file") as mock_apply,
    ):
        updated = TrackMetadataService(db_session).update_metadata(
            track.id,
            artist="deadmau5",
            title="Strobe",
        )

    assert updated.genre == "Techno"
    assert updated.subgenre == "Minimal Techno"
    assert updated.musicbrainz_recording_id == "mbid-techno"
    mock_apply.assert_called_once()


def test_update_metadata_writes_manual_genre_and_subgenre(db_session, tmp_path: Path) -> None:
    wav = tmp_path / "processing" / "wrong - name.wav"
    wav.parent.mkdir(parents=True)
    _minimal_wav(wav)
    track = Track(
        source_path=str(tmp_path / "watch" / wav.name),
        processing_path=str(wav),
        status=TrackStatus.REVIEW,
        artist="deadmau5",
        title="Strobe",
    )
    db_session.add(track)
    db_session.commit()
    _settings(db_session, tmp_path)

    with (
        patch("app.services.track_metadata_service.notify_pipeline_changed"),
        patch("app.services.track_metadata_service.resolve_track_genres") as mock_resolve,
        patch("app.services.track_metadata_service.apply_resolved_genres_to_file") as mock_apply,
    ):
        updated = TrackMetadataService(db_session).update_metadata(
            track.id,
            artist="deadmau5",
            title="Strobe",
            genre="house",
            subgenre="deep house",
        )

    assert updated.genre == "House"
    assert updated.subgenre == "Deep House"
    mock_resolve.assert_not_called()
    mock_apply.assert_called_once()


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


def test_update_metadata_routes_to_duplicates_on_name_collision(
    db_session, tmp_path: Path
) -> None:
    from app.models.duplicate_group import DuplicateGroup
    from app.models.fingerprint import Fingerprint

    ready_dir = tmp_path / "ready"
    review_dir = tmp_path / "review"
    dup_dir = tmp_path / "duplicates"
    for key, path in (
        ("ready_folder", ready_dir),
        ("review_folder", review_dir),
        ("duplicates_folder", dup_dir),
        ("naming_template", "{title} - {artist} ({mix}){ext}"),
    ):
        db_session.add(Setting(key=key, value=str(path) if path != "{title} - {artist} ({mix}){ext}" else path))
    db_session.commit()

    hash_value = "metacollision1"
    library_name = "Strobe - deadmau5 (Original Mix).wav"

    keeper_file = ready_dir / library_name
    keeper_file.parent.mkdir(parents=True)
    _minimal_wav(keeper_file)

    review_file = review_dir / "wrong - name.wav"
    review_file.parent.mkdir(parents=True)
    _minimal_wav(review_file)

    keeper = Track(
        source_path=str(tmp_path / "watch" / "keeper.wav"),
        final_path=str(keeper_file),
        status=TrackStatus.READY,
        artist="deadmau5",
        title="Strobe",
    )
    duplicate = Track(
        source_path=str(tmp_path / "watch" / "dup.wav"),
        final_path=str(review_file),
        status=TrackStatus.REVIEW,
    )
    db_session.add_all([keeper, duplicate])
    db_session.commit()

    group = DuplicateGroup(fingerprint_hash=hash_value)
    db_session.add(group)
    db_session.flush()
    for track in (keeper, duplicate):
        db_session.add(
            Fingerprint(
                track_id=track.id,
                duplicate_group_id=group.id,
                fingerprint_hash=hash_value,
            )
        )
    db_session.commit()

    with patch("app.services.track_metadata_service.notify_pipeline_changed"):
        updated = TrackMetadataService(db_session).update_metadata(
            duplicate.id,
            artist="deadmau5",
            title="Strobe",
        )

    assert updated.status == TrackStatus.DUPLICATE
    assert updated.final_path is not None
    assert hash_value in updated.final_path
    assert library_name in updated.final_path
    assert Path(updated.final_path).is_file()
    assert keeper_file.is_file()
