from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.fingerprint.chromaprint import FingerprintError, compute_fingerprint
from app.fingerprint.version_priority import preferred_track_ids
from app.logging import get_logger
from app.models.duplicate_group import DuplicateGroup
from app.models.enums import JobStatus, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.track import Track
from app.services.queue_service import QueueService
from app.utils.job_payload import job_payload
from app.services.settings_service import SettingsService
from app.utils.workspace_files import (
    clear_stale_processing_copy,
    move_into_destination,
    remove_watch_source,
)

logger = get_logger("DUPLICATES")


class FingerprintService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def process_fingerprint_job(self, job: Job) -> None:
        track = self._get_track(job.source_path)
        if track is None:
            job.status = JobStatus.FAILED
            job.error_message = f"No track for source: {job.source_path}"
            self._db.commit()
            return

        if not track.processing_path or not Path(track.processing_path).is_file():
            job.status = JobStatus.FAILED
            job.error_message = "Processing file missing for fingerprint"
            track.status = TrackStatus.FAILED
            self._db.commit()
            return

        existing_fp = self._get_fingerprint_for_track(track.id)
        if existing_fp is not None:
            job.status = JobStatus.COMPLETED
            self._db.commit()
            self._after_fingerprint(track, existing_fp.fingerprint_hash, job)
            logger.info("fingerprint_skipped_already_done", source=job.source_path)
            return

        audio_path = Path(track.processing_path)
        try:
            data = compute_fingerprint(audio_path)
        except FingerprintError as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            track.status = TrackStatus.FAILED
            self._db.commit()
            logger.error("fingerprint_failed", source=job.source_path, error=str(exc))
            return

        group = self._get_or_create_group(data.fingerprint_hash)
        fp = Fingerprint(
            track_id=track.id,
            duplicate_group_id=group.id,
            fingerprint_hash=data.fingerprint_hash,
            raw_fingerprint=data.raw_fingerprint,
            duration_seconds=data.duration_seconds,
        )
        self._db.add(fp)
        job.status = JobStatus.COMPLETED
        self._db.commit()

        logger.info(
            "fingerprint_complete",
            source=job.source_path,
            hash=data.fingerprint_hash[:12],
        )
        self._after_fingerprint(track, data.fingerprint_hash, job)

    def _after_fingerprint(self, track: Track, fingerprint_hash: str, job: Job) -> None:
        self._db.refresh(track)
        force_tag = bool(job_payload(job).get("reprocess"))
        queue = QueueService(self._db)
        if force_tag:
            queue.enqueue_tag(track.source_path, force=True)
            logger.info("reprocess_tag_enqueued", source=track.source_path)
            return
        group = self._get_group_by_hash(fingerprint_hash)
        if group is not None and group.preferred_track_id is not None:
            if track.id == group.preferred_track_id:
                queue.enqueue_tag(track.source_path, force=force_tag)
                logger.info("duplicate_manual_preferred_for_tag", source=track.source_path)
            else:
                self._route_to_duplicates_folder(track, fingerprint_hash)
            return

        group_tracks = self._tracks_in_group(fingerprint_hash)
        preferred_ids = preferred_track_ids(group_tracks)

        if track.id in preferred_ids:
            queue.enqueue_tag(track.source_path, force=force_tag)
            logger.info("duplicate_preferred_for_tag", source=track.source_path)
            return

        self._route_to_duplicates_folder(track, fingerprint_hash)

    def _get_group_by_hash(self, fingerprint_hash: str) -> DuplicateGroup | None:
        return self._db.execute(
            select(DuplicateGroup).where(DuplicateGroup.fingerprint_hash == fingerprint_hash)
        ).scalar_one_or_none()

    def route_to_duplicates_folder(
        self,
        track: Track,
        fingerprint_hash: str,
        *,
        target_name: str | None = None,
    ) -> None:
        if (
            track.status == TrackStatus.DUPLICATE
            and track.final_path
            and Path(track.final_path).is_file()
        ):
            track.processing_path = clear_stale_processing_copy(
                processing_path=track.processing_path,
                final_path=track.final_path,
            )
            self._db.commit()
            settings = SettingsService(self._db).get_all()
            if remove_watch_source(track.source_path, Path(settings.watch_folder)):
                logger.info("watch_source_removed", source=track.source_path)
            return

        audio = self._audio_file(track)
        if audio is None:
            track.status = TrackStatus.FAILED
            self._db.commit()
            return

        settings = SettingsService(self._db).get_all()
        dup_root = Path(settings.duplicates_folder) / fingerprint_hash
        dup_root.mkdir(parents=True, exist_ok=True)
        dest = dup_root / (target_name or audio.name)
        if dest.exists() and track.final_path != str(dest):
            stem = Path(target_name).stem if target_name else audio.stem
            suffix = Path(target_name).suffix if target_name else audio.suffix
            dest = dup_root / f"{stem}_{track.id}{suffix}"

        dest = move_into_destination(audio, dest)
        track.final_path = str(dest)
        track.processing_path = None
        track.status = TrackStatus.DUPLICATE
        self._db.commit()
        if remove_watch_source(track.source_path, Path(settings.watch_folder)):
            logger.info("watch_source_removed", source=track.source_path)
        logger.info(
            "duplicate_routed",
            source=track.source_path,
            dest=str(dest),
        )

    def _audio_file(self, track: Track) -> Path | None:
        for path_str in (track.processing_path, track.final_path):
            if not path_str:
                continue
            path = Path(path_str)
            if path.is_file():
                return path
        return None

    def _route_to_duplicates_folder(self, track: Track, fingerprint_hash: str) -> None:
        self.route_to_duplicates_folder(track, fingerprint_hash)

    def _get_or_create_group(self, fingerprint_hash: str) -> DuplicateGroup:
        group = self._db.execute(
            select(DuplicateGroup).where(DuplicateGroup.fingerprint_hash == fingerprint_hash)
        ).scalar_one_or_none()
        if group is not None:
            return group
        group = DuplicateGroup(fingerprint_hash=fingerprint_hash)
        self._db.add(group)
        self._db.flush()
        return group

    def _tracks_in_group(self, fingerprint_hash: str) -> list[Track]:
        rows = (
            self._db.execute(
                select(Track)
                .join(Fingerprint, Fingerprint.track_id == Track.id)
                .where(Fingerprint.fingerprint_hash == fingerprint_hash)
            )
            .scalars()
            .all()
        )
        return list(rows)

    def _get_fingerprint_for_track(self, track_id: int) -> Fingerprint | None:
        return self._db.execute(
            select(Fingerprint).where(Fingerprint.track_id == track_id)
        ).scalar_one_or_none()

    def _get_track(self, source_path: str) -> Track | None:
        return self._db.execute(
            select(Track).where(Track.source_path == source_path)
        ).scalar_one_or_none()
