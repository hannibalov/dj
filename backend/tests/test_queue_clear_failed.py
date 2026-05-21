from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.services.queue_service import QueueService


def test_clear_failed_jobs_removes_only_failed(db_session: Session) -> None:
    db_session.add(
        Job(
            job_type=JobType.TAG,
            status=JobStatus.FAILED,
            source_path="/watch/a.mp3",
            error_message="boom",
        )
    )
    db_session.add(
        Job(
            job_type=JobType.ANALYZE,
            status=JobStatus.FAILED,
            source_path="/watch/b.mp3",
        )
    )
    db_session.add(
        Job(
            job_type=JobType.INGEST,
            status=JobStatus.PENDING,
            source_path="/watch/c.mp3",
        )
    )
    db_session.add(
        Job(
            job_type=JobType.ROUTE,
            status=JobStatus.COMPLETED,
            source_path="/watch/d.mp3",
        )
    )
    db_session.commit()

    deleted = QueueService(db_session).clear_failed_jobs()

    assert deleted == 2
    remaining = db_session.execute(select(Job)).scalars().all()
    assert len(remaining) == 2
    assert all(j.status != JobStatus.FAILED for j in remaining)


def test_clear_failed_jobs_noop_when_none(db_session: Session) -> None:
    assert QueueService(db_session).clear_failed_jobs() == 0
