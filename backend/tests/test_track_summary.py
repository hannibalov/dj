from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.track import Track
from app.services.track_service import TrackService


def test_status_summary_counts_by_db_status_and_pipeline_stage(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            Track(source_path="/watch/a.mp3", status=TrackStatus.INGESTED),
            Track(source_path="/watch/b.mp3", status=TrackStatus.INGESTED),
            Track(source_path="/watch/c.mp3", status=TrackStatus.READY),
            Track(source_path="/watch/d.mp3", status=TrackStatus.FAILED),
        ]
    )
    db_session.commit()

    summary = TrackService(db_session).status_summary()

    assert summary.total == 4
    assert summary.by_status == {"ingested": 2, "ready": 1, "failed": 1}
    assert summary.by_pipeline_stage["awaiting_analyze"] == 2
    assert summary.by_pipeline_stage["ready"] == 1
    assert summary.by_pipeline_stage["failed"] == 1


def test_status_summary_splits_ingested_tracks_by_progress(
    db_session: Session,
) -> None:
    awaiting = Track(source_path="/watch/await.mp3", status=TrackStatus.INGESTED)
    analyzed = Track(
        source_path="/watch/analyzed.mp3",
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
    )
    fingerprinted = Track(
        source_path="/watch/fp.mp3",
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
    )
    tagged = Track(
        source_path="/watch/tagged.mp3",
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
        tagged_at=datetime.now(UTC),
    )
    db_session.add_all([awaiting, analyzed, fingerprinted, tagged])
    db_session.commit()

    for track in (fingerprinted, tagged):
        db_session.add(
            Fingerprint(
                track_id=track.id,
                fingerprint_hash=f"hash-{track.id}",
                raw_fingerprint="raw",
                duration_seconds=180.0,
            )
        )
    db_session.commit()

    summary = TrackService(db_session).status_summary()

    assert summary.by_pipeline_stage["awaiting_analyze"] == 1
    assert summary.by_pipeline_stage["awaiting_fingerprint"] == 1
    assert summary.by_pipeline_stage["awaiting_tag"] == 1
    assert summary.by_pipeline_stage["awaiting_route"] == 1
