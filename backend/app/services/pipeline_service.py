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
        track_service = TrackService(self._db)
        return PipelineSnapshot(
            queue=queue,
            tracks=track_service.list_tracks(),
            track_summary=track_service.status_summary(),
            worker_active=queue.running > 0,
            queue_stalled=queue.pending > 0 and queue.running == 0,
            queue_backlogged=queue.pending > 0,
            last_event=get_last_pipeline_event(),
        )
