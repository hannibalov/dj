from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    INGEST = "ingest"
    ANALYZE = "analyze"
    FINGERPRINT = "fingerprint"
    TAG = "tag"
    ROUTE = "route"


class TrackStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    INGESTED = "ingested"
    READY = "ready"
    REVIEW = "review"
    DUPLICATE = "duplicate"
    ARCHIVED = "archived"
    FAILED = "failed"
