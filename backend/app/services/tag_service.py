"""Metadata tagging and library renaming in processing workspace."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging import get_logger
from app.metadata.matcher import match_track_metadata, needs_metadata_review
from app.metadata.rename import build_library_filename
from app.metadata.tags import write_tags
from app.models.enums import JobStatus, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.track import Track
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService

logger = get_logger("TAGGER")


class TagService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def process_tag_job(self, job: Job) -> None:
        track = self._get_track(job.source_path)
        if track is None:
            job.status = JobStatus.FAILED
            job.error_message = f"No track for source: {job.source_path}"
            self._db.commit()
            return

        if not track.processing_path or not Path(track.processing_path).is_file():
            job.status = JobStatus.FAILED
            job.error_message = "Processing file missing for tagging"
            track.status = TrackStatus.FAILED
            self._db.commit()
            return

        if track.tagged_at is not None:
            job.status = JobStatus.COMPLETED
            self._db.commit()
            QueueService(self._db).enqueue_route(track.source_path)
            logger.info("tag_skipped_already_done", source=job.source_path)
            return

        audio_path = Path(track.processing_path)
        env = get_settings()
        settings = SettingsService(self._db).get_all()
        fp = self._get_fingerprint(track.id)

        match = match_track_metadata(
            audio_path,
            raw_fingerprint=fp.raw_fingerprint if fp else None,
            duration_seconds=fp.duration_seconds if fp else None,
            acoustid_api_key=env.acoustid_api_key,
            confidence_threshold=settings.tag_confidence_threshold,
        )

        threshold = settings.tag_confidence_threshold
        review = needs_metadata_review(match, threshold=threshold)

        if match is None:
            track.needs_metadata_review = True
            track.tag_confidence = 0.0
            track.tagged_at = datetime.now(UTC)
            job.status = JobStatus.COMPLETED
            self._db.commit()
            logger.info("tag_no_match", source=job.source_path)
            QueueService(self._db).enqueue_route(track.source_path)
            return

        new_name = build_library_filename(
            artist=match.artist,
            title=match.title,
            mix=match.mix_version,
            extension=audio_path.suffix,
            template=settings.naming_template,
        )
        dest = audio_path.with_name(new_name)
        if dest != audio_path:
            dest = self._unique_dest(dest, track.id)
            audio_path.rename(dest)
            track.processing_path = str(dest)
            audio_path = dest

        try:
            write_tags(
                audio_path,
                artist=match.artist,
                title=match.title,
                album=match.album,
            )
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = f"Failed to write tags: {exc}"
            self._db.commit()
            logger.error("tag_write_failed", source=job.source_path, error=str(exc))
            return

        track.artist = match.artist
        track.title = match.title
        track.album = match.album
        track.mix_version = match.mix_version
        track.musicbrainz_recording_id = match.musicbrainz_recording_id
        track.tag_confidence = match.confidence
        track.needs_metadata_review = review
        track.tagged_at = datetime.now(UTC)
        job.status = JobStatus.COMPLETED
        self._db.commit()

        logger.info(
            "tag_complete",
            source=job.source_path,
            artist=match.artist,
            title=match.title,
            confidence=match.confidence,
            review=review,
        )
        QueueService(self._db).enqueue_route(track.source_path)

    @staticmethod
    def _unique_dest(dest: Path, track_id: int) -> Path:
        if not dest.exists():
            return dest
        return dest.with_name(f"{dest.stem}_{track_id}{dest.suffix}")

    def _get_fingerprint(self, track_id: int) -> Fingerprint | None:
        return self._db.execute(
            select(Fingerprint).where(Fingerprint.track_id == track_id)
        ).scalar_one_or_none()

    def _get_track(self, source_path: str) -> Track | None:
        return self._db.execute(
            select(Track).where(Track.source_path == source_path)
        ).scalar_one_or_none()
