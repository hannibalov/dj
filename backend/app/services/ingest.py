import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.models.enums import JobStatus, TrackStatus
from app.models.job import Job
from app.models.track import Track
from app.services.settings_service import SettingsService
from app.services.stability import FileStabilityChecker

logger = get_logger("ROUTER")


class IngestService:
    """Copy stable files from watch/incoming into the processing workspace."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def process_ingest_job(self, job: Job) -> None:
        settings = SettingsService(self._db).get_all()
        source = Path(job.source_path)
        track = self._get_or_create_track(source)

        if self._already_ingested(track):
            track.status = TrackStatus.INGESTED
            job.status = JobStatus.COMPLETED
            self._db.commit()
            logger.info(
                "ingest_skipped_already_present",
                source=str(source),
                dest=track.processing_path,
            )
            return

        track.status = TrackStatus.PROCESSING
        self._db.commit()

        checker = FileStabilityChecker(
            settings.stability_poll_seconds,
            settings.stability_required_seconds,
        )
        if not checker.wait_until_stable(source):
            track.status = TrackStatus.FAILED
            job.status = JobStatus.FAILED
            job.error_message = f"Source file not stable or missing: {source}"
            self._db.commit()
            return

        processing_root = Path(settings.processing_folder)
        processing_root.mkdir(parents=True, exist_ok=True)

        dest = processing_root / source.name
        if dest.exists() and track.processing_path != str(dest):
            dest = processing_root / f"{source.stem}_{job.id}{source.suffix}"

        shutil.copy2(source, dest)
        logger.info("ingest_copied", source=str(source), dest=str(dest))

        track.processing_path = str(dest)
        track.status = TrackStatus.INGESTED
        job.status = JobStatus.COMPLETED
        self._db.commit()

    def _get_or_create_track(self, source: Path) -> Track:
        track = self._db.execute(
            select(Track).where(Track.source_path == str(source))
        ).scalar_one_or_none()
        if track is None:
            track = Track(source_path=str(source), status=TrackStatus.QUEUED)
            self._db.add(track)
            self._db.flush()
        return track

    @staticmethod
    def _already_ingested(track: Track) -> bool:
        if not track.processing_path:
            return False
        return Path(track.processing_path).is_file()
