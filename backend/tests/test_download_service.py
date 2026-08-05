from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.models.setting import Setting
from app.services.download_service import DownloadService
from app.services.queue_service import QueueService


def test_enqueue_download(db_session: Session) -> None:
    url = "https://www.youtube.com/watch?v=abc123"
    result = QueueService(db_session).enqueue_download(url)
    assert result.enqueued
    assert result.job is not None
    assert result.job.job_type == JobType.DOWNLOAD
    assert result.job.source_path == url


def test_enqueue_download_skips_duplicate_pending(db_session: Session) -> None:
    url = "https://www.youtube.com/watch?v=abc123"
    queue = QueueService(db_session)
    first = queue.enqueue_download(url)
    second = queue.enqueue_download(url)
    assert first.enqueued
    assert not second.enqueued
    assert second.skip_reason == "already_queued"


def test_download_service_completes_job(db_session: Session, tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    output = watch / "Artist - Title.mp3"
    output.write_bytes(b"mp3")

    db_session.add(Setting(key="watch_folder", value=str(watch)))
    db_session.commit()

    url = "https://www.youtube.com/watch?v=abc123"
    job = Job(job_type=JobType.DOWNLOAD, status=JobStatus.PENDING, source_path=url)
    db_session.add(job)
    db_session.commit()

    with patch(
        "app.services.download_service.download_youtube_audio",
        return_value=output,
    ):
        result = DownloadService(db_session).process_download_job(job)

    assert result == str(output)
    assert job.status == JobStatus.COMPLETED
    assert job.payload is not None
    assert "output_path" in job.payload


def test_worker_chains_ingest_after_download(db_session: Session, tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    output = watch / "Artist - Title.mp3"
    output.write_bytes(b"mp3")

    db_session.add(Setting(key="watch_folder", value=str(watch)))
    db_session.commit()

    url = "https://www.youtube.com/watch?v=abc123"
    queue = QueueService(db_session)
    download_job = queue.enqueue_download(url).job
    assert download_job is not None

    with patch(
        "app.services.download_service.download_youtube_audio",
        return_value=output,
    ):
        output_path = DownloadService(db_session).process_download_job(download_job)

    assert output_path == str(output)
    from app.workers.main import _chain_after_download

    _chain_after_download(queue, download_job, output_path)

    ingest_jobs = (
        db_session.execute(
            select(Job).where(Job.job_type == JobType.INGEST, Job.source_path == str(output))
        )
        .scalars()
        .all()
    )
    assert len(ingest_jobs) == 1


def test_download_youtube_api(client: TestClient) -> None:
    response = client.post(
        "/downloads/youtube",
        json={"url": "https://www.youtube.com/watch?v=abc123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enqueued"] is True
    assert data["job_id"] is not None


def test_download_youtube_api_rejects_invalid_url(client: TestClient) -> None:
    response = client.post(
        "/downloads/youtube",
        json={"url": "https://example.com/not-youtube"},
    )
    assert response.status_code == 422
