from pathlib import Path
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.setting import Setting
from app.models.track import Track
from app.services.routing_service import RoutingService


def _folders(db_session: Session, tmp_path: Path) -> None:
    db_session.add(Setting(key="watch_folder", value=str(tmp_path / "watch")))
    db_session.add(Setting(key="ready_folder", value=str(tmp_path / "ready")))
    db_session.add(Setting(key="review_folder", value=str(tmp_path / "review")))
    db_session.commit()


def test_routes_to_ready_when_loudness_ok(db_session: Session, tmp_path: Path) -> None:
    watch_file = tmp_path / "watch" / "song.mp3"
    watch_file.parent.mkdir(parents=True)
    watch_file.write_bytes(b"watch")
    processing = tmp_path / "processing" / "song.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    _folders(db_session, tmp_path)

    track = Track(
        source_path=str(watch_file),
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
        true_peak_db=-1.0,
    )
    job = Job(job_type=JobType.ROUTE, status=JobStatus.PENDING, source_path=track.source_path)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    RoutingService(db_session).process_route_job(job)
    db_session.refresh(track)
    db_session.refresh(job)

    assert job.status == JobStatus.COMPLETED
    assert track.status == TrackStatus.READY
    assert track.final_path is not None
    assert Path(track.final_path).is_file()
    assert "ready" in track.final_path
    assert track.processing_path is None
    assert not processing.exists()
    assert not watch_file.exists()


def test_routes_to_review_when_too_quiet(db_session: Session, tmp_path: Path) -> None:
    watch_file = tmp_path / "watch" / "quiet.mp3"
    watch_file.parent.mkdir(parents=True)
    watch_file.write_bytes(b"watch")
    processing = tmp_path / "processing" / "quiet.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    _folders(db_session, tmp_path)

    track = Track(
        source_path=str(watch_file),
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
        integrated_lufs=-22.0,
        true_peak_db=-2.0,
    )
    job = Job(job_type=JobType.ROUTE, status=JobStatus.PENDING, source_path=track.source_path)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    RoutingService(db_session).process_route_job(job)
    db_session.refresh(track)

    assert track.status == TrackStatus.REVIEW
    assert track.final_path is not None
    assert "review" in track.final_path
    assert watch_file.is_file()


def test_routes_to_review_when_mp3_below_quality_gate(
    db_session: Session,
    tmp_path: Path,
) -> None:
    watch_file = tmp_path / "watch" / "low.mp3"
    watch_file.parent.mkdir(parents=True)
    watch_file.write_bytes(b"watch")
    processing = tmp_path / "processing" / "low.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    _folders(db_session, tmp_path)
    db_session.add(Setting(key="review_min_mp3_bitrate_kbps", value="320"))
    db_session.commit()

    track = Track(
        source_path=str(watch_file),
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
        true_peak_db=-1.0,
    )
    job = Job(job_type=JobType.ROUTE, status=JobStatus.PENDING, source_path=track.source_path)
    db_session.add(track)
    db_session.add(job)
    db_session.commit()

    with patch("app.router.rules.get_format_info") as mock_format:
        from app.utils.audio_format import AudioFormatInfo

        mock_format.return_value = AudioFormatInfo(
            extension=".mp3",
            family="mp3",
            format_rank=3,
            bitrate_kbps=128,
        )
        RoutingService(db_session).process_route_job(job)

    db_session.refresh(track)
    assert track.status == TrackStatus.REVIEW
