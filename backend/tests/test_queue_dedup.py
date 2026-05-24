from pathlib import Path

from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.setting import Setting
from app.models.track import Track
from app.services.ingest import IngestService
from app.services.queue_service import SKIP_ALREADY_INGESTED, SKIP_ALREADY_QUEUED, QueueService


def _set_watch_folder(db_session: Session, path: Path) -> None:
    db_session.add(Setting(key="watch_folder", value=str(path)))
    db_session.commit()


def _set_processing_folder(db_session: Session, path: Path) -> None:
    db_session.add(Setting(key="processing_folder", value=str(path)))
    db_session.commit()


def test_enqueue_skips_when_job_pending(db_session: Session, tmp_path: Path) -> None:
    source = tmp_path / "track.mp3"
    source.write_bytes(b"x")
    queue = QueueService(db_session)
    first = queue.enqueue_ingest(str(source))
    second = queue.enqueue_ingest(str(source))
    assert first.enqueued is True
    assert second.enqueued is False
    assert second.skip_reason == SKIP_ALREADY_QUEUED


def test_enqueue_skips_when_already_ingested(db_session: Session, tmp_path: Path) -> None:
    source = tmp_path / "track.mp3"
    processing = tmp_path / "processing" / "track.mp3"
    processing.parent.mkdir()
    source.write_bytes(b"x")
    processing.write_bytes(b"x")
    track = Track(
        source_path=str(source),
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
    )
    db_session.add(track)
    db_session.commit()

    result = QueueService(db_session).enqueue_ingest(str(source))
    assert result.enqueued is False
    assert result.skip_reason == SKIP_ALREADY_INGESTED


def test_enqueue_skips_when_duplicate_already_routed(db_session: Session, tmp_path: Path) -> None:
    source = tmp_path / "watch" / "dup.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"x")
    final = tmp_path / "duplicates" / "hash123" / "dup.mp3"
    final.parent.mkdir(parents=True)
    final.write_bytes(b"x")
    track = Track(
        source_path=str(source),
        final_path=str(final),
        status=TrackStatus.DUPLICATE,
    )
    db_session.add(track)
    db_session.commit()

    result = QueueService(db_session).enqueue_ingest(str(source))
    assert result.enqueued is False
    assert result.skip_reason == SKIP_ALREADY_INGESTED


def test_rescan_counts_skipped(db_session: Session, tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    track = watch / "a.mp3"
    track.write_bytes(b"x")
    processing = tmp_path / "processing" / "a.mp3"
    processing.parent.mkdir()
    processing.write_bytes(b"x")
    db_session.add(
        Track(
            source_path=str(track),
            processing_path=str(processing),
            status=TrackStatus.INGESTED,
        )
    )
    _set_watch_folder(db_session, watch)
    result = QueueService(db_session).enqueue_watch_folder_scan()
    assert result.enqueued == 0
    assert result.skipped == 1


def test_ingest_idempotent_when_processing_file_exists(db_session: Session, tmp_path: Path) -> None:
    source = tmp_path / "watch" / "song.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"audio")
    dest = tmp_path / "processing" / "song.mp3"
    dest.parent.mkdir()
    dest.write_bytes(b"audio")
    _set_processing_folder(db_session, tmp_path / "processing")

    job = Job(job_type=JobType.INGEST, status=JobStatus.PENDING, source_path=str(source))
    db_session.add(
        Track(
            source_path=str(source),
            processing_path=str(dest),
            status=TrackStatus.INGESTED,
        )
    )
    db_session.add(job)
    db_session.commit()

    IngestService(db_session).process_ingest_job(job)
    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert len(list((tmp_path / "processing").glob("*.mp3"))) == 1
