from datetime import datetime

from pydantic import BaseModel

from app.schemas.queue import QueueResponse
from app.schemas.track import TrackResponse
from app.schemas.track_summary import TrackStatusSummary


class PipelineEvent(BaseModel):
    message: str
    at: datetime


class PipelineSnapshot(BaseModel):
    queue: QueueResponse
    tracks: list[TrackResponse]
    track_summary: TrackStatusSummary
    worker_active: bool
    queue_stalled: bool = False
    queue_backlogged: bool = False
    last_event: PipelineEvent | None = None
