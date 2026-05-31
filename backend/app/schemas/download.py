from pydantic import BaseModel, Field, field_validator

from app.download.youtube import is_youtube_url


class YouTubeDownloadRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not is_youtube_url(cleaned):
            raise ValueError("Must be a YouTube watch, Shorts, or youtu.be URL")
        return cleaned


class YouTubeDownloadResponse(BaseModel):
    status: str
    enqueued: bool
    job_id: int | None = None
    skip_reason: str | None = None
    message: str
