from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.track import Track
from app.services.song_duplicate_service import SongDuplicateService


def test_list_song_groups_by_musicbrainz_recording_id(db_session: Session, tmp_path: Path) -> None:
    tagged_at = datetime.now(UTC)
    t1 = Track(
        source_path=str(tmp_path / "a.mp3"),
        status=TrackStatus.REVIEW,
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-firestarter",
        tagged_at=tagged_at,
        integrated_lufs=-8.7,
        energy=85,
    )
    t2 = Track(
        source_path=str(tmp_path / "b.mp3"),
        status=TrackStatus.REVIEW,
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-firestarter",
        tagged_at=tagged_at,
        integrated_lufs=-21.5,
        energy=13,
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    db_session.add(
        Fingerprint(track_id=t1.id, fingerprint_hash="hash-a", duplicate_group_id=None)
    )
    db_session.add(
        Fingerprint(track_id=t2.id, fingerprint_hash="hash-b", duplicate_group_id=None)
    )
    db_session.commit()

    groups = SongDuplicateService(db_session).list_groups()
    assert len(groups) == 1
    assert groups[0].match_type == "musicbrainz"
    assert groups[0].musicbrainz_recording_id == "mbid-firestarter"
    assert len(groups[0].members) == 2


def test_list_song_groups_by_metadata_when_no_mbid(db_session: Session, tmp_path: Path) -> None:
    tagged_at = datetime.now(UTC)
    t1 = Track(
        source_path=str(tmp_path / "a.mp3"),
        status=TrackStatus.READY,
        artist="deadmau5",
        title="Strobe",
        mix_version="Original Mix",
        tagged_at=tagged_at,
    )
    t2 = Track(
        source_path=str(tmp_path / "b.mp3"),
        status=TrackStatus.REVIEW,
        artist="deadmau5",
        title="Strobe",
        mix_version="Original Mix",
        tagged_at=tagged_at,
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    db_session.add(Fingerprint(track_id=t1.id, fingerprint_hash="hash-1", duplicate_group_id=None))
    db_session.add(Fingerprint(track_id=t2.id, fingerprint_hash="hash-2", duplicate_group_id=None))
    db_session.commit()

    groups = SongDuplicateService(db_session).list_groups()
    assert len(groups) == 1
    assert groups[0].match_type == "metadata"
    assert groups[0].group_key.startswith("meta:")


def test_list_song_groups_excludes_identical_fingerprints(db_session: Session, tmp_path: Path) -> None:
    tagged_at = datetime.now(UTC)
    t1 = Track(
        source_path=str(tmp_path / "a.mp3"),
        status=TrackStatus.READY,
        artist="Artist",
        title="Title",
        tagged_at=tagged_at,
    )
    t2 = Track(
        source_path=str(tmp_path / "b.mp3"),
        status=TrackStatus.DUPLICATE,
        artist="Artist",
        title="Title",
        tagged_at=tagged_at,
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    same_hash = "identical-hash"
    db_session.add(
        Fingerprint(track_id=t1.id, fingerprint_hash=same_hash, duplicate_group_id=None)
    )
    db_session.add(
        Fingerprint(track_id=t2.id, fingerprint_hash=same_hash, duplicate_group_id=None)
    )
    db_session.commit()

    assert SongDuplicateService(db_session).list_groups() == []


def test_list_song_groups_excludes_untagged_tracks(db_session: Session, tmp_path: Path) -> None:
    t1 = Track(
        source_path=str(tmp_path / "a.mp3"),
        status=TrackStatus.INGESTED,
        artist="Artist",
        title="Title",
    )
    t2 = Track(
        source_path=str(tmp_path / "b.mp3"),
        status=TrackStatus.INGESTED,
        artist="Artist",
        title="Title",
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    db_session.add(Fingerprint(track_id=t1.id, fingerprint_hash="hash-1", duplicate_group_id=None))
    db_session.add(Fingerprint(track_id=t2.id, fingerprint_hash="hash-2", duplicate_group_id=None))
    db_session.commit()

    assert SongDuplicateService(db_session).list_groups() == []
