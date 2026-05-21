from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.track import Track
from app.services.track_service import TrackService


def test_status_summary_counts_all_tracks(db_session: Session) -> None:
    for i, status in enumerate(
        (TrackStatus.INGESTED, TrackStatus.INGESTED, TrackStatus.READY, TrackStatus.FAILED)
    ):
        db_session.add(Track(source_path=f"/watch/{i}.mp3", status=status))
    db_session.commit()

    summary = TrackService(db_session).status_summary()
    assert summary.total == 4
    assert summary.by_status["ingested"] == 2
    assert summary.by_status["ready"] == 1
    assert summary.by_status["failed"] == 1
