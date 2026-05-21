from pydantic import BaseModel

from app.schemas.track import TrackResponse


class TrackActionResponse(BaseModel):
    status: str
    track: TrackResponse
    message: str | None = None


class TrackDeleteResponse(BaseModel):
    status: str
    message: str
    deleted_count: int = 1
