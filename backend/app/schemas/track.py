from datetime import datetime

from pydantic import BaseModel

from app.models.enums import TrackStatus


class TrackResponse(BaseModel):
    id: int
    status: TrackStatus
    pipeline_stage: str = "queued"
    source_path: str
    processing_path: str | None
    final_path: str | None
    artist: str | None
    title: str | None
    album: str | None
    genre: str | None = None
    subgenre: str | None = None
    mix_version: str | None
    musicbrainz_recording_id: str | None
    tag_confidence: float | None
    needs_metadata_review: bool
    tagged_at: datetime | None
    bpm: float | None
    musical_key: str | None
    camelot: str | None
    energy: int | None
    scale: str | None
    bpm_confidence: float | None
    key_confidence: float | None
    integrated_lufs: float | None
    true_peak_db: float | None
    format_extension: str | None = None
    audio_family: str | None = None
    bitrate_kbps: int | None = None
    sample_rate_hz: int | None = None
    bits_per_sample: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
