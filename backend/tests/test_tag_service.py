from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.metadata.matcher import MetadataMatch
from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.track import Track
from app.services.tag_service import TagService


def _folders(db_session: Session, tmp_path: Path) -> None:
    from app.models.setting import Setting

    db_session.add(Setting(key="ready_folder", value=str(tmp_path / "ready")))
    db_session.add(Setting(key="review_folder", value=str(tmp_path / "review")))
    db_session.commit()


def test_tag_renames_and_enqueues_route(db_session: Session, tmp_path: Path) -> None:
    processing = tmp_path / "processing" / "Wonderwall - Oasis.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "Wonderwall - Oasis.mp3")

    track = Track(
        source_path=source,
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
    )
    job = Job(job_type=JobType.TAG, status=JobStatus.PENDING, source_path=source)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    match = MetadataMatch(
        artist="Oasis",
        title="Wonderwall",
        album=None,
        mix_version=None,
        musicbrainz_recording_id="mbid-1",
        confidence=0.92,
        source="acoustid",
    )

    with (
        patch("app.services.tag_service.match_track_metadata", return_value=match),
        patch("app.services.tag_service.write_tags"),
    ):
        TagService(db_session).process_tag_job(job)

    db_session.refresh(track)
    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert track.artist == "Oasis"
    assert track.title == "Wonderwall"
    assert track.tagged_at is not None
    assert track.needs_metadata_review is False
    assert track.processing_path is not None
    processing_file = Path(track.processing_path)
    assert processing_file.name == "Wonderwall - Oasis (Original Mix).mp3"
    assert processing_file.is_file()

    route_jobs = (
        db_session.execute(
            select(Job).where(Job.job_type == JobType.ROUTE, Job.source_path == source)
        )
        .scalars()
        .all()
    )
    assert len(route_jobs) == 1


def test_tag_low_confidence_sets_metadata_review(db_session: Session, tmp_path: Path) -> None:
    processing = tmp_path / "processing" / "unknown.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "unknown.mp3")

    track = Track(
        source_path=source,
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
    )
    job = Job(job_type=JobType.TAG, status=JobStatus.PENDING, source_path=source)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    match = MetadataMatch(
        artist="Some Artist",
        title="Some Title",
        album=None,
        mix_version=None,
        musicbrainz_recording_id=None,
        confidence=0.3,
        source="filename",
    )

    with (
        patch("app.services.tag_service.match_track_metadata", return_value=match),
        patch("app.services.tag_service.write_tags"),
    ):
        TagService(db_session).process_tag_job(job)

    db_session.refresh(track)
    assert track.needs_metadata_review is True


def test_route_sends_low_metadata_confidence_to_review(db_session: Session, tmp_path: Path) -> None:
    _folders(db_session, tmp_path)
    renamed = tmp_path / "processing" / "Wonderwall - Oasis (Original Mix).mp3"
    renamed.parent.mkdir(parents=True)
    renamed.write_bytes(b"audio")

    track = Track(
        source_path=str(tmp_path / "watch" / "song.mp3"),
        processing_path=str(renamed),
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
        true_peak_db=-1.0,
        artist="Oasis",
        title="Wonderwall",
        needs_metadata_review=True,
    )
    from datetime import UTC, datetime

    track.tagged_at = datetime.now(UTC)
    job = Job(job_type=JobType.ROUTE, status=JobStatus.PENDING, source_path=track.source_path)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    from app.services.routing_service import RoutingService

    RoutingService(db_session).process_route_job(job)
    db_session.refresh(track)

    assert track.status == TrackStatus.REVIEW
    assert track.final_path is not None
    assert "review" in track.final_path
    assert Path(track.final_path).name == renamed.name
