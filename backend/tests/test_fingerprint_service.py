from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.fingerprint.chromaprint import FingerprintData
from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.setting import Setting
from app.models.track import Track
from app.services.fingerprint_service import FingerprintService


def _folders(db_session: Session, tmp_path: Path) -> None:
    db_session.add(Setting(key="duplicates_folder", value=str(tmp_path / "duplicates")))
    db_session.add(Setting(key="ready_folder", value=str(tmp_path / "ready")))
    db_session.add(Setting(key="review_folder", value=str(tmp_path / "review")))
    db_session.commit()


def test_fingerprint_enqueues_tag_for_unique_track(db_session: Session, tmp_path: Path) -> None:
    processing = tmp_path / "processing" / "song.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "song.mp3")

    track = Track(
        source_path=source,
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
    )
    job = Job(job_type=JobType.FINGERPRINT, status=JobStatus.PENDING, source_path=source)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    fp_data = FingerprintData(
        fingerprint_hash="abc123unique",
        duration_seconds=200.0,
        raw_fingerprint="raw",
    )
    with patch("app.services.fingerprint_service.compute_fingerprint", return_value=fp_data):
        FingerprintService(db_session).process_fingerprint_job(job)

    db_session.refresh(track)
    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert db_session.execute(select(Fingerprint)).scalar_one() is not None

    tag_jobs = (
        db_session.execute(
            select(Job).where(Job.job_type == JobType.TAG, Job.source_path == source)
        )
        .scalars()
        .all()
    )
    assert len(tag_jobs) == 1


def test_fingerprint_routes_duplicate_copy_to_duplicates_folder(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    hash_value = "sharedhash123"

    preferred = tmp_path / "processing" / "best.mp3"
    duplicate = tmp_path / "processing" / "worse.mp3"
    watch_best = tmp_path / "watch" / "best.mp3"
    watch_worse = tmp_path / "watch" / "worse.mp3"
    watch_best.parent.mkdir(parents=True)
    watch_best.write_bytes(b"watch-best")
    watch_worse.write_bytes(b"watch-worse")
    preferred.parent.mkdir(parents=True)
    preferred.write_bytes(b"preferred")
    duplicate.write_bytes(b"duplicate")
    db_session.add(Setting(key="watch_folder", value=str(tmp_path / "watch")))
    db_session.commit()

    track_a = Track(
        source_path=str(watch_best),
        processing_path=str(preferred),
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
    )
    track_b = Track(
        source_path=str(watch_worse),
        processing_path=str(duplicate),
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
    )
    db_session.add_all([track_a, track_b])
    db_session.commit()

    fp_data = FingerprintData(
        fingerprint_hash=hash_value,
        duration_seconds=180.0,
        raw_fingerprint="raw",
    )

    with patch("app.services.fingerprint_service.compute_fingerprint", return_value=fp_data):
        job_a = Job(
            job_type=JobType.FINGERPRINT,
            status=JobStatus.PENDING,
            source_path=track_a.source_path,
        )
        db_session.add(job_a)
        db_session.commit()
        FingerprintService(db_session).process_fingerprint_job(job_a)

    with (
        patch("app.services.fingerprint_service.compute_fingerprint", return_value=fp_data),
        patch(
            "app.services.fingerprint_service.preferred_track_ids",
            return_value={track_a.id},
        ),
    ):
        job_b = Job(
            job_type=JobType.FINGERPRINT,
            status=JobStatus.PENDING,
            source_path=track_b.source_path,
        )
        db_session.add(job_b)
        db_session.commit()
        FingerprintService(db_session).process_fingerprint_job(job_b)

    db_session.refresh(track_b)
    assert track_b.status == TrackStatus.DUPLICATE
    assert track_b.final_path is not None
    assert "duplicates" in track_b.final_path
    assert hash_value in track_b.final_path
    assert Path(track_b.final_path).is_file()
    assert track_b.processing_path is None
    assert not duplicate.exists()
    assert not watch_worse.exists()
    assert watch_best.is_file()
