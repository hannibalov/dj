from datetime import datetime

from pydantic import BaseModel

from app.models.enums import JobStatus, JobType


class JobResponse(BaseModel):
    id: int
    job_type: JobType
    status: JobStatus
    source_path: str
    attempts: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueueResponse(BaseModel):
    pending: int
    running: int
    failed: int
    completed: int
    jobs: list[JobResponse]


class RescanResponse(BaseModel):
    status: str
    enqueued: int
    skipped: int


class AnalyzeBacklogResponse(BaseModel):
    status: str
    enqueued: int
    skipped: int


class GenreBackfillResponse(BaseModel):
    status: str
    enriched: int
    skipped: int


class LibrarySyncResponse(BaseModel):
    status: str
    enqueued: int
    skipped: int
    paths_repaired: int
    metadata_updated: int
    missing_files: int
    orphan_files: int


class ClearFailedJobsResponse(BaseModel):
    status: str
    deleted_count: int
    message: str


class CleanupResponse(BaseModel):
    status: str
    deleted: int
    message: str


class MetadataSanityResponse(BaseModel):
    status: str
    scanned: int
    flagged_possible_swap: int
    flagged_artist_in_title: int
    artist_in_title_ratio: float
    anomaly: bool
