from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.track import Track
from app.schemas.track import TrackResponse


class TrackService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_tracks(self, limit: int = 100) -> list[TrackResponse]:
        rows = (
            self._db.execute(select(Track).order_by(Track.created_at.desc()).limit(limit))
            .scalars()
            .all()
        )
        return [TrackResponse.model_validate(r) for r in rows]

    def get_track(self, track_id: int) -> TrackResponse | None:
        row = self._db.get(Track, track_id)
        return TrackResponse.model_validate(row) if row else None
