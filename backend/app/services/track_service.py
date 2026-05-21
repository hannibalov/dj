from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.track import Track
from app.schemas.track import TrackResponse
from app.schemas.track_summary import TrackStatusSummary


class TrackService:
    # Dashboard table cap; pipeline counts use count_by_status() for full totals.
    DEFAULT_LIST_LIMIT = 500

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_tracks(self, limit: int | None = None) -> list[TrackResponse]:
        cap = limit if limit is not None else self.DEFAULT_LIST_LIMIT
        rows = (
            self._db.execute(select(Track).order_by(Track.updated_at.desc()).limit(cap))
            .scalars()
            .all()
        )
        return [TrackResponse.model_validate(r) for r in rows]

    def status_summary(self) -> TrackStatusSummary:
        rows = self._db.execute(
            select(Track.status, func.count()).group_by(Track.status)
        ).all()
        by_status = {status.value: count for status, count in rows}
        total = sum(by_status.values())
        return TrackStatusSummary(total=total, by_status=by_status)

    def get_track(self, track_id: int) -> TrackResponse | None:
        row = self._db.get(Track, track_id)
        return TrackResponse.model_validate(row) if row else None
