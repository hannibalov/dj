from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.paths import DATA_DIR, PROJECT_ROOT, sqlite_url_for

_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DJ_",
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"
    database_url: str = Field(default_factory=sqlite_url_for)

    watch_folder: Path = Field(default_factory=lambda: DATA_DIR / "watch")
    incoming_folder: Path = Field(default_factory=lambda: DATA_DIR / "incoming")
    processing_folder: Path = Field(default_factory=lambda: DATA_DIR / "processing")
    ready_folder: Path = Field(default_factory=lambda: DATA_DIR / "ready")
    review_folder: Path = Field(default_factory=lambda: DATA_DIR / "review")
    duplicates_folder: Path = Field(default_factory=lambda: DATA_DIR / "duplicates")
    archive_folder: Path = Field(default_factory=lambda: DATA_DIR / "archive")
    failed_folder: Path = Field(default_factory=lambda: DATA_DIR / "failed")
    logs_folder: Path = Field(default_factory=lambda: DATA_DIR / "logs")
    rekordbox_export_folder: Path = Field(default_factory=lambda: DATA_DIR / "rekordbox")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_internal_url: str = "http://127.0.0.1:8000"

    stability_poll_seconds: float = Field(
        default=2.0,
        description="Interval between stability checks",
    )
    stability_required_seconds: float = Field(
        default=10.0,
        description="File must be unchanged for this duration",
    )

    worker_cpu_limit: float = 1.0
    worker_mem_limit: str = "1g"

    review_lufs_threshold: float = Field(
        default=-18.0,
        description="Integrated LUFS below this → review folder",
    )
    review_true_peak_db: float = Field(
        default=3.0,
        description="True peak above this (dBTP) → review folder",
    )
    review_min_mp3_bitrate_kbps: int = Field(
        default=320,
        description="MP3 below this kbps → review folder (0 = disabled)",
    )
    review_min_lossless_bit_depth: int = Field(
        default=16,
        description="Lossless below this bit depth → review folder (0 = disabled)",
    )
    review_min_lossless_sample_rate_hz: int = Field(
        default=44100,
        description="Lossless below this sample rate → review folder (0 = disabled)",
    )

    acoustid_api_key: str | None = Field(
        default=None,
        description="AcoustID API key for metadata lookup (https://acoustid.org/new-application)",
    )
    tag_confidence_threshold: float = Field(
        default=0.5,
        description="Matches below this score are routed to review/",
    )
    naming_template: str = Field(
        default="{title} - {artist} ({mix}){ext}",
        description="Library filename template after tagging",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
