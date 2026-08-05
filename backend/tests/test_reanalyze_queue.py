import json
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.result import AnalysisResult
from app.metadata.matcher import MetadataMatch
from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.setting import Setting
from app.models.track import Track
from app.services.analysis_service import AnalysisService
from app.services.queue_service import QueueService
from app.services.tag_service import TagService


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


def test_enqueue_reanalyze_all_clears_lufs_and_enqueues(
    db_session: Session, tmp_path: Path
) -> None:
    processing = tmp_path / "processing" / "song.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "song.mp3")

    track = Track(
        source_path=source,
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
        integrated_lufs=-70.0,
        true_peak_db=1.5,
        bpm=120.0,
        artist="Old",
        title="Name",
    )
    from datetime import UTC, datetime

    track.tagged_at = datetime.now(UTC)
    db_session.add(track)
    db_session.commit()

    result = QueueService(db_session).enqueue_reanalyze_all()
    db_session.refresh(track)

    assert result.enqueued == 1
    assert track.integrated_lufs is None
    assert track.bpm is None
    assert track.artist is None
    assert track.title is None
    assert track.tagged_at is None
    assert track.status == TrackStatus.INGESTED

    jobs = (
        db_session.execute(
            select(Job).where(Job.job_type == JobType.ANALYZE, Job.source_path == source)
        )
        .scalars()
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.PENDING
    assert json.loads(jobs[0].payload or "{}") == {"reprocess": True}


def test_enqueue_reanalyze_all_sets_reprocess_for_library_tracks(
    db_session: Session, tmp_path: Path
) -> None:
    ready_file = tmp_path / "ready" / "song.mp3"
    ready_file.parent.mkdir(parents=True)
    ready_file.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "song.mp3")

    track = Track(
        source_path=source,
        final_path=str(ready_file),
        status=TrackStatus.READY,
        integrated_lufs=-70.0,
    )
    db_session.add(track)
    db_session.commit()

    result = QueueService(db_session).enqueue_reanalyze_all()

    assert result.enqueued == 1
    job = db_session.execute(
        select(Job).where(Job.job_type == JobType.ANALYZE, Job.source_path == source)
    ).scalar_one()
    assert json.loads(job.payload or "{}") == {"reprocess": True}
    db_session.refresh(track)
    assert track.status == TrackStatus.INGESTED


def test_reanalyze_ready_track_runs_tag_and_sets_artist_title(
    db_session: Session, tmp_path: Path
) -> None:
    """Full reprocess: analyze → fingerprint → tag (not route-only)."""
    _folders(db_session, tmp_path)
    ready_file = tmp_path / "ready" / "raw.mp3"
    ready_file.parent.mkdir(parents=True)
    ready_file.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "raw.mp3")

    track = Track(
        source_path=source,
        final_path=str(ready_file),
        status=TrackStatus.READY,
        integrated_lufs=-14.0,
    )
    db_session.add(track)
    db_session.commit()
    db_session.add(
        Fingerprint(
            track_id=track.id,
            fingerprint_hash="abc123",
            raw_fingerprint="fp",
            duration_seconds=200.0,
        )
    )
    db_session.commit()

    QueueService(db_session).enqueue_reanalyze_all()
    analyze_job = db_session.execute(
        select(Job).where(Job.job_type == JobType.ANALYZE, Job.source_path == source)
    ).scalar_one()

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
        patch("app.services.analysis_service.analyze_audio", return_value=mock_result),
        patch("app.services.tag_service.match_track_metadata", return_value=match),
        patch("app.services.tag_service.write_tags"),
    ):
        AnalysisService(db_session).process_analyze_job(analyze_job)

        from app.services.fingerprint_service import FingerprintService

        fp_job = db_session.execute(
            select(Job).where(
                Job.job_type == JobType.FINGERPRINT,
                Job.source_path == source,
                Job.status == JobStatus.PENDING,
            )
        ).scalar_one()
        FingerprintService(db_session).process_fingerprint_job(fp_job)

        tag_job = db_session.execute(
            select(Job).where(
                Job.job_type == JobType.TAG,
                Job.source_path == source,
                Job.status == JobStatus.PENDING,
            )
        ).scalar_one()
        TagService(db_session).process_tag_job(tag_job)

    db_session.refresh(track)
    assert track.artist == "Oasis"
    assert track.title == "Wonderwall"
    assert track.integrated_lufs == -12.5
    assert track.processing_path is not None
    assert Path(track.processing_path).is_file()
    assert track.final_path is None

    route_jobs = (
        db_session.execute(
            select(Job).where(Job.job_type == JobType.ROUTE, Job.source_path == source)
        )
        .scalars()
        .all()
    )
    assert len(route_jobs) == 1


def test_reprocess_fingerprint_always_enqueues_tag_even_if_not_preferred_duplicate(
    db_session: Session, tmp_path: Path
) -> None:
    """Reanalyze must not skip TAG by sending the track to duplicates/."""
    _folders(db_session, tmp_path)
    from app.models.duplicate_group import DuplicateGroup

    processing = tmp_path / "processing" / "copy.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "copy.mp3")

    group = DuplicateGroup(fingerprint_hash="duphash", preferred_track_id=999)
    db_session.add(group)
    db_session.flush()

    track = Track(
        source_path=source,
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
    )
    db_session.add(track)
    db_session.commit()
    db_session.add(
        Fingerprint(
            track_id=track.id,
            duplicate_group_id=group.id,
            fingerprint_hash="duphash",
            raw_fingerprint="fp",
            duration_seconds=180.0,
        )
    )
    db_session.commit()

    job = Job(
        job_type=JobType.FINGERPRINT,
        status=JobStatus.PENDING,
        source_path=source,
        payload='{"reprocess": true}',
    )
    db_session.add(job)
    db_session.commit()

    from app.services.fingerprint_service import FingerprintService

    FingerprintService(db_session).process_fingerprint_job(job)

    tag_job = db_session.execute(
        select(Job).where(Job.job_type == JobType.TAG, Job.source_path == source)
    ).scalar_one_or_none()
    assert tag_job is not None
    assert tag_job.status == JobStatus.PENDING
    db_session.refresh(track)
    assert track.status != TrackStatus.DUPLICATE


def test_analyze_reprocess_enqueues_fingerprint_not_route(
    db_session: Session, tmp_path: Path
) -> None:
    _folders(db_session, tmp_path)
    processing = tmp_path / "processing" / "song.mp3"
    processing.parent.mkdir(parents=True)
    processing.write_bytes(b"audio")
    source = str(tmp_path / "watch" / "song.mp3")

    track = Track(
        source_path=source,
        processing_path=str(processing),
        status=TrackStatus.INGESTED,
    )
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
    assert len(fp_jobs) >= 1
    assert route_jobs == []
