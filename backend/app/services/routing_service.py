from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.models.enums import JobStatus, TrackStatus
from app.models.job import Job
from app.models.track import Track
from app.router.rules import needs_quality_review_for_path, needs_review
from app.services.settings_service import SettingsService
from app.utils.workspace_files import (
    clear_stale_processing_copy,
    move_into_destination,
    remove_watch_source,
)

logger = get_logger("ROUTER")


class RoutingService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def process_route_job(self, job: Job) -> None:
        track = self._get_track(job.source_path)
        if track is None:
            job.status = JobStatus.FAILED
            job.error_message = f"No track for source: {job.source_path}"
            self._db.commit()
            return

        if (
            track.status in (TrackStatus.READY, TrackStatus.REVIEW, TrackStatus.DUPLICATE)
            and track.final_path
            and Path(track.final_path).is_file()
            and track.processing_path
            and Path(track.processing_path).is_file()
        ):
            track.processing_path = clear_stale_processing_copy(
                processing_path=track.processing_path,
                final_path=track.final_path,
            )
            job.status = JobStatus.COMPLETED
            self._db.commit()
            logger.info("route_skipped_already_routed", source=job.source_path)
            return

        if track.status == TrackStatus.DUPLICATE:
            job.status = JobStatus.COMPLETED
            self._db.commit()
            logger.info("route_skipped_duplicate", source=job.source_path)
            return

        if not track.processing_path or not Path(track.processing_path).is_file():
            job.status = JobStatus.FAILED
            job.error_message = "Processing file missing for routing"
            track.status = TrackStatus.FAILED
            self._db.commit()
            return

        settings = SettingsService(self._db).get_all()
        loudness_review = needs_review(
            integrated_lufs=track.integrated_lufs,
            true_peak_db=track.true_peak_db,
            lufs_threshold=settings.review_lufs_threshold,
            peak_threshold=settings.review_true_peak_db,
        )
        quality_review = needs_quality_review_for_path(
            Path(track.processing_path),
            min_mp3_bitrate_kbps=settings.review_min_mp3_bitrate_kbps,
            min_lossless_bit_depth=settings.review_min_lossless_bit_depth,
            min_lossless_sample_rate_hz=settings.review_min_lossless_sample_rate_hz,
        )
        review = loudness_review or quality_review or track.needs_metadata_review

        source_file = Path(track.processing_path)
        dest_root = Path(settings.review_folder if review else settings.ready_folder)
        dest_root.mkdir(parents=True, exist_ok=True)
        dest = dest_root / source_file.name
        if dest.exists() and track.final_path != str(dest):
            dest = dest_root / f"{source_file.stem}_{track.id}{source_file.suffix}"

        dest = move_into_destination(source_file, dest)
        track.final_path = str(dest)
        track.processing_path = None
        track.status = TrackStatus.REVIEW if review else TrackStatus.READY
        job.status = JobStatus.COMPLETED
        self._db.commit()

        if not review:
            removed = remove_watch_source(job.source_path, Path(settings.watch_folder))
            if removed:
                logger.info("watch_source_removed", source=job.source_path)

        logger.info(
            "route_complete",
            source=job.source_path,
            dest=str(dest),
            status=track.status.value,
            review=review,
        )
        self._notify_song_duplicate_review()

    def _notify_song_duplicate_review(self) -> None:
        from app.services.notify import notify_pipeline_changed
        from app.services.song_duplicate_service import SongDuplicateService

        groups = SongDuplicateService(self._db).list_groups()
        if groups:
            notify_pipeline_changed(
                f"Same-song review: {len(groups)} group(s) need comparison"
            )

    def _get_track(self, source_path: str) -> Track | None:
        return self._db.execute(
            select(Track).where(Track.source_path == source_path)
        ).scalar_one_or_none()
