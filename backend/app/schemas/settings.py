from pydantic import BaseModel, Field


class FolderSettings(BaseModel):
    watch_folder: str
    incoming_folder: str
    processing_folder: str
    ready_folder: str
    review_folder: str
    duplicates_folder: str
    archive_folder: str
    failed_folder: str
    logs_folder: str
    rekordbox_export_folder: str


class SettingsResponse(FolderSettings):
    stability_poll_seconds: float = 2.0
    stability_required_seconds: float = 10.0
    tag_confidence_threshold: float = 0.5
    naming_template: str = "{title} - {artist} ({mix}){ext}"
    review_lufs_threshold: float = -18.0
    review_true_peak_db: float = -0.1


class SettingsUpdate(BaseModel):
    folders: FolderSettings | None = None
    stability_poll_seconds: float | None = Field(default=None, gt=0)
    stability_required_seconds: float | None = Field(default=None, gt=0)
    tag_confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    naming_template: str | None = None
    review_lufs_threshold: float | None = None
    review_true_peak_db: float | None = None
