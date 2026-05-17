from pydantic import BaseModel

from app.schemas.track import TrackResponse


class TrackActionResponse(BaseModel):
    status: str
    track: TrackResponse
    message: str | None = None
