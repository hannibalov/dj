from pydantic import BaseModel

from app.models.enums import TrackStatus


class DuplicateGroupMember(BaseModel):
    track_id: int
    status: TrackStatus
    source_path: str
    final_path: str | None
    fingerprint_hash: str
    duration_seconds: float | None
    format_extension: str | None
    bitrate_kbps: int | None


class DuplicateGroupResponse(BaseModel):
    id: int
    fingerprint_hash: str
    members: list[DuplicateGroupMember]


class DuplicateResolveResponse(BaseModel):
    status: str
