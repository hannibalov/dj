from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.track import Track
from app.workers.scheduler import run_scheduled_check


def _polluted_track(tmp_path: Path) -> Track:
    return Track(
        source_path=str(tmp_path / "polluted.mp3"),
        artist="Daft Punk",
        title="Daft Punk - One More Time",
        status=TrackStatus.INGESTED,
    )


def test_first_call_with_no_last_run_executes_and_returns_now(
    db_session: Session, tmp_path: Path
) -> None:
    track = _polluted_track(tmp_path)
    db_session.add(track)
    db_session.commit()

    now = datetime.now(UTC)
    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = run_scheduled_check(db_session, last_run=None, now=now, interval_minutes=60.0)

    assert result == now
    db_session.refresh(track)
    assert track.metadata_issue == "artist_in_title"


def test_does_not_rerun_before_interval_elapses(db_session: Session, tmp_path: Path) -> None:
    track = _polluted_track(tmp_path)
    db_session.add(track)
    db_session.commit()

    first_run = datetime.now(UTC)
    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = run_scheduled_check(
            db_session, last_run=None, now=first_run, interval_minutes=60.0
        )
    assert result == first_run

    # Manually clear the flag to prove a second, too-soon call is a no-op.
    db_session.refresh(track)
    track.metadata_issue = None
    db_session.commit()

    later = first_run + timedelta(minutes=1)
    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = run_scheduled_check(
            db_session, last_run=first_run, now=later, interval_minutes=60.0
        )

    assert result == first_run
    db_session.refresh(track)
    assert track.metadata_issue is None


def test_reruns_once_interval_has_elapsed(db_session: Session, tmp_path: Path) -> None:
    track = _polluted_track(tmp_path)
    db_session.add(track)
    db_session.commit()

    first_run = datetime.now(UTC)
    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = run_scheduled_check(
            db_session, last_run=None, now=first_run, interval_minutes=60.0
        )
    assert result == first_run

    db_session.refresh(track)
    track.metadata_issue = None
    db_session.commit()

    much_later = first_run + timedelta(minutes=61)
    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = run_scheduled_check(
            db_session, last_run=first_run, now=much_later, interval_minutes=60.0
        )

    assert result == much_later
    db_session.refresh(track)
    assert track.metadata_issue == "artist_in_title"
