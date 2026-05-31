import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.download.youtube import YouTubeDownloadError, download_youtube_audio
from app.logging import get_logger
from app.models.enums import JobStatus
from app.models.job import Job
from app.services.settings_service import SettingsService

logger = get_logger("ROUTER")


class DownloadService:
    """Download remote audio into the watch folder for ingest."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def process_download_job(self, job: Job) -> str | None:
        """Run yt-dlp for job.source_path (YouTube URL). Returns output path on success."""
        settings = SettingsService(self._db).get_all()
        watch_folder = Path(settings.watch_folder)
        url = job.source_path

        try:
            output_path = download_youtube_audio(url, watch_folder)
        except YouTubeDownloadError as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            self._db.commit()
            logger.warning("youtube_download_failed", url=url, error=str(exc))
            return None

        job.status = JobStatus.COMPLETED
        job.payload = json.dumps({"url": url, "output_path": str(output_path)})
        self._db.commit()
        logger.info("youtube_download_complete", url=url, output=str(output_path))
        return str(output_path)
