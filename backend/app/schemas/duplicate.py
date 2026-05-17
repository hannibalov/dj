from pydantic import BaseModel, Field

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
    artist: str | None = None
    title: str | None = None
    integrated_lufs: float | None = None


class DuplicateGroupResponse(BaseModel):
    id: int
    fingerprint_hash: str
    preferred_track_id: int | None = None
    members: list[DuplicateGroupMember]


class DuplicateResolveRequest(BaseModel):
    group_id: int
    keep_track_id: int
    archive_track_ids: list[int] | None = None


class DuplicateResolveResponse(BaseModel):
    status: str
    kept_track_id: int | None = None
    archived_track_ids: list[int] = Field(default_factory=list)
