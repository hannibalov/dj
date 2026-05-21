from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.services.queue_service import QueueService


def test_reset_interrupted_jobs_returns_running_to_pending(db_session: Session) -> None:
    job = Job(
        job_type=JobType.ANALYZE,
        status=JobStatus.RUNNING,
        source_path="/data/watch/song.mp3",
    )
    db_session.add(job)
    db_session.commit()

    count = QueueService(db_session).reset_interrupted_jobs()
    db_session.refresh(job)

    assert count == 1
    assert job.status == JobStatus.PENDING
