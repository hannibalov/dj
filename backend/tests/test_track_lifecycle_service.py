from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.duplicate_group import DuplicateGroup
from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.setting import Setting
from app.models.track import Track
from app.services.track_lifecycle_service import TrackLifecycleError, TrackLifecycleService


def _folders(db_session: Session, tmp_path: Path) -> None:
    for key, name in (
        ("watch_folder", "watch"),
        ("processing_folder", "processing"),
        ("ready_folder", "ready"),
        ("review_folder", "review"),
        ("duplicates_folder", "duplicates"),
    ):
        db_session.add(Setting(key=key, value=str(tmp_path / name)))
    db_session.commit()


def test_reset_deletes_library_copy_and_enqueues_ingest(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    watch_file = tmp_path / "watch" / "song.mp3"
    watch_file.parent.mkdir(parents=True)
    watch_file.write_bytes(b"watch")
    review_file = tmp_path / "review" / "song.mp3"
    review_file.parent.mkdir(parents=True)
    review_file.write_bytes(b"review")

    track = Track(
        source_path=str(watch_file),
        processing_path=None,
        final_path=str(review_file),
        status=TrackStatus.REVIEW,
        integrated_lufs=-20.0,
        artist="A",
        title="B",
    )
    db_session.add(track)
    db_session.commit()

    with patch("app.services.track_lifecycle_service.notify_pipeline_changed"):
        TrackLifecycleService(db_session).reset_track(track.id)

    db_session.refresh(track)
    assert not review_file.exists()
    assert track.status == TrackStatus.QUEUED
    assert track.final_path is None
    assert track.integrated_lufs is None
    assert track.artist is None

    ingest = db_session.execute(
        select(Job).where(Job.job_type == JobType.INGEST, Job.source_path == str(watch_file))
    ).scalar_one()
    assert ingest.status == JobStatus.PENDING


def test_reset_restores_ready_copy_to_watch_when_watch_missing(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    watch_path = tmp_path / "watch" / "song.mp3"
    ready_file = tmp_path / "ready" / "Song - Artist (Original Mix).mp3"
    ready_file.parent.mkdir(parents=True)
    ready_file.write_bytes(b"ready")

    track = Track(
        source_path=str(watch_path),
        final_path=str(ready_file),
        status=TrackStatus.READY,
        integrated_lufs=-14.0,
        artist="Artist",
        title="Song",
    )
    db_session.add(track)
    db_session.commit()

    with patch("app.services.track_lifecycle_service.notify_pipeline_changed"):
        TrackLifecycleService(db_session).reset_track(track.id)

    assert watch_path.is_file()
    assert not ready_file.exists()
    db_session.refresh(track)
    assert track.status == TrackStatus.QUEUED
    assert track.final_path is None


def test_reset_fails_when_watch_and_library_copy_missing(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    track = Track(
        source_path=str(tmp_path / "watch" / "gone.mp3"),
        status=TrackStatus.READY,
    )
    db_session.add(track)
    db_session.commit()

    with pytest.raises(TrackLifecycleError, match="No file in watch folder"):
        TrackLifecycleService(db_session).reset_track(track.id)


def test_delete_failed_track_removes_files_jobs_and_db_row(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    processing_file = tmp_path / "processing" / "bad.mp3"
    processing_file.parent.mkdir(parents=True)
    processing_file.write_bytes(b"bad")
    watch_file = tmp_path / "watch" / "bad.mp3"
    watch_file.parent.mkdir(parents=True)
    watch_file.write_bytes(b"watch")

    track = Track(
        source_path=str(watch_file),
        processing_path=str(processing_file),
        status=TrackStatus.FAILED,
    )
    db_session.add(track)
    db_session.commit()
    db_session.add(
        Job(
            job_type=JobType.ANALYZE,
            source_path=str(watch_file),
            status=JobStatus.FAILED,
            error_message="boom",
        )
    )
    db_session.commit()

    with patch("app.services.track_lifecycle_service.notify_pipeline_changed"):
        TrackLifecycleService(db_session).delete_failed_track(track.id)

    assert db_session.get(Track, track.id) is None
    assert not processing_file.exists()
    assert not watch_file.exists()
    jobs = db_session.execute(select(Job).where(Job.source_path == str(watch_file))).all()
    assert jobs == []


def test_delete_failed_track_rejects_non_failed(db_session: Session, tmp_path: Path) -> None:
    _folders(db_session, tmp_path)
    track = Track(
        source_path=str(tmp_path / "watch" / "ok.mp3"),
        status=TrackStatus.READY,
    )
    db_session.add(track)
    db_session.commit()

    with pytest.raises(TrackLifecycleError, match="Only failed tracks"):
        TrackLifecycleService(db_session).delete_failed_track(track.id)


def test_delete_all_failed_tracks(db_session: Session, tmp_path: Path) -> None:
    _folders(db_session, tmp_path)
    for name in ("a.mp3", "b.mp3"):
        path = tmp_path / "watch" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
        db_session.add(Track(source_path=str(path), status=TrackStatus.FAILED))
    db_session.add(
        Track(
            source_path=str(tmp_path / "watch" / "ok.mp3"),
            status=TrackStatus.READY,
        )
    )
    db_session.commit()

    with patch("app.services.track_lifecycle_service.notify_pipeline_changed"):
        count = TrackLifecycleService(db_session).delete_all_failed_tracks()

    assert count == 2
    remaining = db_session.execute(select(Track)).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].status == TrackStatus.READY


def test_confirm_review_moves_to_ready_and_removes_sibling_duplicate(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    group = DuplicateGroup(fingerprint_hash="abc123")
    db_session.add(group)
    db_session.flush()

    review_file = tmp_path / "review" / "Artist - Song (Original Mix).mp3"
    review_file.parent.mkdir(parents=True)
    review_file.write_bytes(b"keeper")
    dup_file = tmp_path / "duplicates" / "abc123" / "Artist - Song.mp3"
    dup_file.parent.mkdir(parents=True)
    dup_file.write_bytes(b"dup")

    watch_a = tmp_path / "watch" / "a.mp3"
    watch_a.parent.mkdir(parents=True)
    watch_a.write_bytes(b"watch-a")

    keeper = Track(
        source_path=str(watch_a),
        final_path=str(review_file),
        status=TrackStatus.REVIEW,
    )
    sibling = Track(
        source_path=str(tmp_path / "watch" / "b.mp3"),
        final_path=str(dup_file),
        status=TrackStatus.DUPLICATE,
    )
    db_session.add_all([keeper, sibling])
    db_session.commit()

    db_session.add(
        Fingerprint(
            track_id=keeper.id,
            duplicate_group_id=group.id,
            fingerprint_hash="abc123",
        )
    )
    db_session.add(
        Fingerprint(
            track_id=sibling.id,
            duplicate_group_id=group.id,
            fingerprint_hash="abc123",
        )
    )
    db_session.commit()

    with patch("app.services.track_lifecycle_service.notify_pipeline_changed"):
        result = TrackLifecycleService(db_session).confirm_review(keeper.id)

    assert result.status == TrackStatus.READY
    assert result.final_path is not None
    assert "ready" in result.final_path
    assert Path(result.final_path).is_file()
    assert not review_file.exists()
    assert not dup_file.exists()
    assert not watch_a.exists()

    db_session.refresh(sibling)
    assert sibling.status == TrackStatus.ARCHIVED
    assert sibling.final_path is None


def test_confirm_review_enriches_missing_genres_from_musicbrainz(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    review_file = tmp_path / "review" / "Firestarter - The Prodigy.mp3"
    review_file.parent.mkdir(parents=True)
    review_file.write_bytes(b"audio")

    track = Track(
        source_path=str(tmp_path / "watch" / "song.mp3"),
        final_path=str(review_file),
        status=TrackStatus.REVIEW,
        artist="The Prodigy",
        title="Firestarter",
    )
    db_session.add(track)
    db_session.commit()

    with (
        patch("app.services.track_lifecycle_service.notify_pipeline_changed"),
        patch(
            "app.services.track_lifecycle_service.resolve_track_genres",
            return_value=__import__(
                "app.metadata.musicbrainz_lookup", fromlist=["RecordingGenreInfo"]
            ).RecordingGenreInfo(
                genre="Electronic",
                subgenre="Big Beat",
                musicbrainz_recording_id="mbid-firestarter",
            ),
        ),
        patch("app.services.track_lifecycle_service.apply_resolved_genres_to_file") as mock_write,
    ):
        result = TrackLifecycleService(db_session).confirm_review(track.id)

    assert result.status == TrackStatus.READY
    assert result.genre == "Electronic"
    assert result.subgenre == "Big Beat"
    assert result.musicbrainz_recording_id == "mbid-firestarter"
    mock_write.assert_called_once()
