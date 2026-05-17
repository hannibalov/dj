from datetime import datetime

from pydantic import BaseModel

from app.schemas.queue import QueueResponse
from app.schemas.track import TrackResponse


class PipelineEvent(BaseModel):
    message: str
    at: datetime


class PipelineSnapshot(BaseModel):
    queue: QueueResponse
    tracks: list[TrackResponse]
    worker_active: bool
    last_event: PipelineEvent | None = None
