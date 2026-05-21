from pathlib import Path
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.analysis.result import AnalysisResult
from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.track import Track
from app.services.analysis_service import AnalysisService
from app.services.queue_service import QueueService


def test_analyze_stores_results_and_enqueues_fingerprint(
    db_session: Session, tmp_path: Path
) -> None:
    processing = tmp_path / "processing" / "track.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "track.mp3")

    track = Track(source_path=source, processing_path=str(processing), status=TrackStatus.INGESTED)
    job = Job(job_type=JobType.ANALYZE, status=JobStatus.PENDING, source_path=source)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    mock_result = AnalysisResult(
        bpm=128.0,
        bpm_confidence=0.9,
        musical_key="A",
        scale="minor",
        camelot="8A",
        key_confidence=0.8,
        energy=72,
        integrated_lufs=-12.5,
        true_peak_db=-1.2,
    )

    with patch("app.services.analysis_service.analyze_audio", return_value=mock_result):
        AnalysisService(db_session).process_analyze_job(job)

    db_session.refresh(track)
    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert track.bpm == 128.0
    assert track.camelot == "8A"
    assert track.integrated_lufs == -12.5
    assert track.status == TrackStatus.INGESTED

    from sqlalchemy import select

    fp_jobs = (
        db_session.execute(
            select(Job).where(Job.job_type == JobType.FINGERPRINT, Job.source_path == source)
        )
        .scalars()
        .all()
    )
    assert len(fp_jobs) == 1


def test_analyze_reprocess_enqueues_fingerprint(db_session: Session, tmp_path: Path) -> None:
    processing = tmp_path / "processing" / "track.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "track.mp3")

    track = Track(source_path=source, processing_path=str(processing), status=TrackStatus.INGESTED)
    job = Job(
        job_type=JobType.ANALYZE,
        status=JobStatus.PENDING,
        source_path=source,
        payload='{"reprocess": true}',
    )
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    mock_result = AnalysisResult(
        bpm=128.0,
        bpm_confidence=0.9,
        musical_key="A",
        scale="minor",
        camelot="8A",
        key_confidence=0.8,
        energy=72,
        integrated_lufs=-12.5,
        true_peak_db=-1.2,
    )

    with patch("app.services.analysis_service.analyze_audio", return_value=mock_result):
        AnalysisService(db_session).process_analyze_job(job)

    from sqlalchemy import select

    fp_jobs = (
        db_session.execute(
            select(Job).where(Job.job_type == JobType.FINGERPRINT, Job.source_path == source)
        )
        .scalars()
        .all()
    )
    route_jobs = (
        db_session.execute(
            select(Job).where(
                Job.job_type == JobType.ROUTE,
                Job.source_path == source,
                Job.status == JobStatus.PENDING,
            )
        )
        .scalars()
        .all()
    )
    assert len(fp_jobs) == 1
    assert route_jobs == []


def test_enqueue_analyze_skips_when_already_analyzed(db_session: Session, tmp_path: Path) -> None:
    source = str(tmp_path / "a.mp3")
    db_session.add(
        Track(
            source_path=source,
            integrated_lufs=-14.0,
            status=TrackStatus.INGESTED,
        )
    )
    db_session.commit()
    result = QueueService(db_session).enqueue_analyze(source)
    assert result.enqueued is False
    assert result.skip_reason == "already_analyzed"
