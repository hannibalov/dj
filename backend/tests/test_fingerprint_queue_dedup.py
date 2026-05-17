from pathlib import Path

from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.track import Track
from app.services.queue_service import (
    SKIP_ALREADY_FINGERPRINTED,
    SKIP_ALREADY_QUEUED,
    QueueService,
)


def test_enqueue_fingerprint_skips_when_job_pending(db_session: Session, tmp_path: Path) -> None:
    source = str(tmp_path / "track.mp3")
    db_session.add(
        Job(
            job_type=JobType.FINGERPRINT,
            status=JobStatus.PENDING,
            source_path=source,
        )
    )
    db_session.commit()

    result = QueueService(db_session).enqueue_fingerprint(source)
    assert result.enqueued is False
    assert result.skip_reason == SKIP_ALREADY_QUEUED


def test_enqueue_fingerprint_skips_when_already_fingerprinted(
    db_session: Session, tmp_path: Path
) -> None:
    source = str(tmp_path / "track.mp3")
    track = Track(source_path=source, status=TrackStatus.INGESTED)
    db_session.add(track)
    db_session.commit()
    db_session.add(
        Fingerprint(
            track_id=track.id,
            fingerprint_hash="abc",
        )
    )
    db_session.commit()

    result = QueueService(db_session).enqueue_fingerprint(source)
    assert result.enqueued is False
    assert result.skip_reason == SKIP_ALREADY_FINGERPRINTED
