from sqlalchemy.orm import Session

from app.schemas.pipeline import PipelineEvent, PipelineSnapshot
from app.services.queue_service import QueueService
from app.services.track_service import TrackService

_last_event: PipelineEvent | None = None


def set_last_pipeline_event(message: str) -> PipelineEvent:
    global _last_event
    from datetime import UTC, datetime

    _last_event = PipelineEvent(message=message, at=datetime.now(UTC))
    return _last_event


def get_last_pipeline_event() -> PipelineEvent | None:
    return _last_event


class PipelineService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_snapshot(self) -> PipelineSnapshot:
        queue = QueueService(self._db).get_queue_summary()
        tracks = TrackService(self._db).list_tracks()
        return PipelineSnapshot(
            queue=queue,
            tracks=tracks,
            worker_active=queue.running > 0,
            last_event=get_last_pipeline_event(),
        )
