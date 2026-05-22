from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.track import Track
from app.services.track_service import TrackService


def test_get_track_includes_pipeline_stage_from_progress(db_session: Session) -> None:
    track = Track(
        source_path="/watch/song.mp3",
        status=TrackStatus.INGESTED,
        integrated_lufs=-12.0,
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

    response = TrackService(db_session).get_track(track.id)

    assert response is not None
    assert response.status == TrackStatus.INGESTED
    assert response.pipeline_stage == "awaiting_tag"


def test_list_tracks_includes_pipeline_stage(db_session: Session) -> None:
    ready = Track(source_path="/watch/ready.mp3", status=TrackStatus.READY)
    tagged = Track(
        source_path="/watch/tagged.mp3",
        status=TrackStatus.INGESTED,
        integrated_lufs=-14.0,
        tagged_at=datetime.now(UTC),
    )
    db_session.add_all([ready, tagged])
    db_session.commit()
    db_session.add(
        Fingerprint(
            track_id=tagged.id,
            fingerprint_hash="hash-tagged",
            raw_fingerprint="fp",
            duration_seconds=180.0,
        )
    )
    db_session.commit()

    by_path = {t.source_path: t for t in TrackService(db_session).list_tracks()}

    assert by_path["/watch/ready.mp3"].pipeline_stage == "ready"
    assert by_path["/watch/tagged.mp3"].pipeline_stage == "awaiting_route"
