"""Manual track reset and review approval."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.models.enums import JobStatus, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.track import Track
from app.schemas.settings import SettingsResponse
from app.services.notify import notify_pipeline_changed
from app.services.queue_service import ACTIVE_JOB_STATUSES, QueueService
from app.services.settings_service import SettingsService
from app.metadata.genre_resolve import apply_resolved_genres_to_file, resolve_track_genres
from app.utils.workspace_files import (
    move_into_destination,
    path_is_under_root,
    remove_watch_source,
    remove_workspace_file,
    restore_library_file_to_watch,
)

logger = get_logger("ROUTER")


class TrackLifecycleError(Exception):
    pass


class TrackLifecycleService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def reset_track(self, track_id: int) -> Track:
        track = self._get_track_or_raise(track_id)
        settings = SettingsService(self._db).get_all()
        watch_root = Path(settings.watch_folder)
        source = Path(track.source_path)
        library_file = self._library_copy_path(track, settings)

        if not source.is_file():
            if library_file is None:
                raise TrackLifecycleError("No file in watch folder and no library copy to restore")
            restore_library_file_to_watch(
                library_file,
                source,
                watch_folder=watch_root,
            )
            logger.info(
                "watch_restored_from_library",
                source=track.source_path,
                from_path=str(library_file),
            )
        elif library_file is not None and library_file.is_file():
            remove_workspace_file(library_file)

        self._cancel_active_jobs(track.source_path)
        self._delete_workspace_files(track)
        self._delete_fingerprint(track.id)
        self._clear_track_pipeline_state(track)
        track.status = TrackStatus.QUEUED
        self._db.commit()

        result = QueueService(self._db).enqueue_ingest(track.source_path)
        if not result.enqueued:
            raise TrackLifecycleError(
                f"Could not enqueue ingest: {result.skip_reason or 'unknown'}"
            )

        self._db.refresh(track)
        notify_pipeline_changed(f"Reset queued: {source.name}")
        logger.info("track_reset", track_id=track_id, source=track.source_path)
        return track

    def delete_failed_track(self, track_id: int) -> None:
        track = self._get_track_or_raise(track_id)
        if track.status != TrackStatus.FAILED:
            raise TrackLifecycleError("Only failed tracks can be deleted")
        source = track.source_path
        name = Path(source).name
        self._purge_failed_track(track)
        self._db.commit()
        notify_pipeline_changed(f"Deleted failed track: {name}")
        logger.info("track_delete_failed", track_id=track_id, source=source)

    def delete_all_failed_tracks(self) -> int:
        failed = (
            self._db.execute(select(Track).where(Track.status == TrackStatus.FAILED))
            .scalars()
            .all()
        )
        for track in failed:
            self._purge_failed_track(track)
        count = len(failed)
        if count:
            self._db.commit()
            notify_pipeline_changed(f"Deleted {count} failed track(s)")
            logger.info("tracks_delete_all_failed", count=count)
        return count

    def confirm_review(self, track_id: int) -> Track:
        track = self._get_track_or_raise(track_id)
        if track.status != TrackStatus.REVIEW:
            raise TrackLifecycleError("Track is not in review status")
        if not track.final_path or not Path(track.final_path).is_file():
            raise TrackLifecycleError("Review file missing")

        settings = SettingsService(self._db).get_all()
        watch_root = Path(settings.watch_folder)
        review_root = Path(settings.review_folder).resolve()
        ready_root = Path(settings.ready_folder).resolve()
        final = Path(track.final_path).resolve()
        if review_root not in final.parents:
            raise TrackLifecycleError("Track file is not under the review folder")

        dest = ready_root / final.name
        if dest.exists() and dest.resolve() != final.resolve():
            dest = ready_root / f"{final.stem}_{track.id}{final.suffix}"

        move_into_destination(final, dest)
        track.final_path = str(dest)
        track.processing_path = None
        track.status = TrackStatus.READY
        track.needs_metadata_review = False

        self._enrich_genres_on_approve(track, dest)

        removed = self._remove_sibling_copies(track)
        watch_removed = remove_watch_source(track.source_path, watch_root)
        self._db.commit()
        self._db.refresh(track)

        notify_pipeline_changed(f"Approved to ready: {dest.name}")
        if watch_removed:
            logger.info("watch_source_removed", source=track.source_path)
        logger.info(
            "track_confirm_review",
            track_id=track_id,
            dest=str(dest),
            siblings_cleared=removed,
        )
        return track

    def _enrich_genres_on_approve(self, track: Track, audio_path: Path) -> None:
        """Fill missing genre/subgenre from MusicBrainz before moving to ready."""
        if not track.artist or not track.title:
            return
        if track.genre and track.subgenre:
            return

        genres = resolve_track_genres(
            audio_path=audio_path,
            musicbrainz_recording_id=track.musicbrainz_recording_id,
            artist=track.artist,
            title=track.title,
        )
        if not genres.genre and not genres.subgenre:
            return

        if genres.genre:
            track.genre = genres.genre
        if genres.subgenre:
            track.subgenre = genres.subgenre
        if genres.musicbrainz_recording_id:
            track.musicbrainz_recording_id = genres.musicbrainz_recording_id

        apply_resolved_genres_to_file(
            audio_path,
            genre=track.genre,
            subgenre=track.subgenre,
            artist=track.artist,
            title=track.title,
            album=track.album,
        )
        logger.info(
            "track_genres_enriched_on_approve",
            track_id=track.id,
            genre=track.genre,
            subgenre=track.subgenre,
            musicbrainz_recording_id=track.musicbrainz_recording_id,
        )

    def _remove_sibling_copies(self, keeper: Track) -> int:
        siblings = self._sibling_tracks(keeper.id)
        removed = 0
        for sibling in siblings:
            if sibling.id == keeper.id:
                continue
            if self._delete_workspace_files(sibling):
                removed += 1
            sibling.final_path = None
            sibling.processing_path = None
            if sibling.status in (
                TrackStatus.DUPLICATE,
                TrackStatus.REVIEW,
                TrackStatus.READY,
            ):
                sibling.status = TrackStatus.ARCHIVED
        return removed

    def _sibling_tracks(self, track_id: int) -> list[Track]:
        fp = self._db.execute(
            select(Fingerprint).where(Fingerprint.track_id == track_id)
        ).scalar_one_or_none()
        if fp is None or fp.duplicate_group_id is None:
            return [self._get_track_or_raise(track_id)]

        rows = (
            self._db.execute(
                select(Track)
                .join(Fingerprint, Fingerprint.track_id == Track.id)
                .where(Fingerprint.duplicate_group_id == fp.duplicate_group_id)
            )
            .scalars()
            .all()
        )
        return list(rows)

    def _purge_failed_track(self, track: Track) -> None:
        settings = SettingsService(self._db).get_all()
        watch_root = Path(settings.watch_folder)
        self._cancel_active_jobs(track.source_path)
        self._delete_workspace_files(track)
        self._delete_failed_folder_copy(track, Path(settings.failed_folder))
        self._delete_fingerprint(track.id)
        self._delete_jobs_for_source(track.source_path)
        self._clear_duplicate_group_preference(track.id)
        remove_watch_source(track.source_path, watch_root)
        self._db.delete(track)

    def _delete_failed_folder_copy(self, track: Track, failed_root: Path) -> None:
        if not failed_root.is_dir():
            return
        basename = Path(track.source_path).name
        candidate = failed_root / basename
        if candidate.is_file():
            remove_workspace_file(candidate)

    def _delete_jobs_for_source(self, source_path: str) -> None:
        jobs = (
            self._db.execute(select(Job).where(Job.source_path == source_path)).scalars().all()
        )
        for job in jobs:
            self._db.delete(job)

    def _clear_duplicate_group_preference(self, track_id: int) -> None:
        from app.models.duplicate_group import DuplicateGroup

        groups = (
            self._db.execute(
                select(DuplicateGroup).where(DuplicateGroup.preferred_track_id == track_id)
            )
            .scalars()
            .all()
        )
        for group in groups:
            group.preferred_track_id = None

    def _cancel_active_jobs(self, source_path: str) -> None:
        jobs = (
            self._db.execute(
                select(Job).where(
                    Job.source_path == source_path,
                    Job.status.in_(ACTIVE_JOB_STATUSES),
                )
            )
            .scalars()
            .all()
        )
        for job in jobs:
            job.status = JobStatus.CANCELLED

    def _delete_fingerprint(self, track_id: int) -> None:
        fp = self._db.execute(
            select(Fingerprint).where(Fingerprint.track_id == track_id)
        ).scalar_one_or_none()
        if fp is not None:
            self._db.delete(fp)

    @staticmethod
    def _library_copy_path(track: Track, settings: SettingsResponse) -> Path | None:
        if not track.final_path:
            return None
        final = Path(track.final_path)
        if not final.is_file():
            return None
        ready_root = Path(settings.ready_folder).resolve()
        review_root = Path(settings.review_folder).resolve()
        resolved = final.resolve()
        if path_is_under_root(resolved, ready_root) or path_is_under_root(resolved, review_root):
            return final
        return None

    @staticmethod
    def _delete_workspace_files(track: Track) -> bool:
        deleted = False
        for path_str in (track.final_path, track.processing_path):
            path = Path(path_str) if path_str else None
            if path and path.is_file():
                remove_workspace_file(path)
                deleted = True
        return deleted

    @staticmethod
    def _clear_track_pipeline_state(track: Track) -> None:
        track.processing_path = None
        track.final_path = None
        track.artist = None
        track.title = None
        track.album = None
        track.genre = None
        track.subgenre = None
        track.mix_version = None
        track.musicbrainz_recording_id = None
        track.tag_confidence = None
        track.needs_metadata_review = False
        track.tagged_at = None
        track.bpm = None
        track.musical_key = None
        track.camelot = None
        track.energy = None
        track.scale = None
        track.bpm_confidence = None
        track.key_confidence = None
        track.integrated_lufs = None
        track.true_peak_db = None

    def _get_track_or_raise(self, track_id: int) -> Track:
        track = self._db.get(Track, track_id)
        if track is None:
            raise TrackLifecycleError(f"Track not found: {track_id}")
        return track
