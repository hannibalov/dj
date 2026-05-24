from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import TrackStatus


class SongDuplicateGroupMember(BaseModel):
    track_id: int
    status: TrackStatus
    source_path: str
    final_path: str | None
    fingerprint_hash: str | None = None
    duration_seconds: float | None
    format_extension: str | None
    bitrate_kbps: int | None
    artist: str | None = None
    title: str | None = None
    integrated_lufs: float | None = None
    energy: int | None = None
    bpm: float | None = None
    camelot: str | None = None


class SongDuplicateGroupResponse(BaseModel):
    group_key: str
    match_type: Literal["musicbrainz", "metadata"]
    label: str
    musicbrainz_recording_id: str | None = None
    suggested_keep_track_id: int | None = None
    members: list[SongDuplicateGroupMember]


class SongDuplicateResolveRequest(BaseModel):
    group_key: str
    keep_track_id: int
    archive_track_ids: list[int] | None = None


class SongDuplicateResolveResponse(BaseModel):
    status: str
    kept_track_id: int | None = None
    archived_track_ids: list[int] = Field(default_factory=list)
