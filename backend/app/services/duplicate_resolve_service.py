"""Manual duplicate group resolution — promote keeper, archive others."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.logging import get_logger
from app.models.duplicate_group import DuplicateGroup
from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.track import Track
from app.schemas.duplicate import DuplicateResolveRequest, DuplicateResolveResponse
from app.services.notify import notify_pipeline_changed

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.schemas.settings import SettingsResponse
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.utils.workspace_files import (
    clear_stale_processing_copy,
    move_into_destination,
    path_is_under_root,
)

logger = get_logger("DUPLICATES")


class DuplicateResolveError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DuplicateResolveService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def resolve(self, body: DuplicateResolveRequest) -> DuplicateResolveResponse:
        group = self._db.get(DuplicateGroup, body.group_id)
        if group is None:
            raise DuplicateResolveError("Duplicate group not found", status_code=404)

        members = self._members_for_group(group.id)
        member_by_id = {t.id: t for t in members}
        keeper = member_by_id.get(body.keep_track_id)
        if keeper is None:
            raise DuplicateResolveError(
                "keep_track_id is not a member of this group",
                status_code=404,
            )

        if keeper.status == TrackStatus.ARCHIVED:
            raise DuplicateResolveError("Cannot keep an archived track", status_code=409)

        archive_ids = self._resolve_archive_ids(body, members, keeper.id)
        for track_id in archive_ids:
            if track_id not in member_by_id:
                raise DuplicateResolveError(
                    f"archive_track_ids contains unknown member: {track_id}",
                    status_code=422,
                )
            if track_id == keeper.id:
                raise DuplicateResolveError("Cannot archive the kept track", status_code=422)

        settings = SettingsService(self._db).get_all()
        group.preferred_track_id = keeper.id
        group.resolved_at = datetime.now(UTC)

        archived_track_ids: list[int] = []
        for track in members:
            if track.id == keeper.id:
                self._promote_keeper(track, group, settings)
            elif track.id in archive_ids:
                self._archive_member(track, group, settings)
                archived_track_ids.append(track.id)

        self._db.commit()
        notify_pipeline_changed(f"Duplicate resolved: kept track {keeper.id}")

        logger.info(
            "duplicate_resolved",
            group_id=group.id,
            kept_track_id=keeper.id,
            archived_track_ids=archived_track_ids,
        )
        return DuplicateResolveResponse(
            status="ok",
            kept_track_id=keeper.id,
            archived_track_ids=archived_track_ids,
        )

    @staticmethod
    def _resolve_archive_ids(
        body: DuplicateResolveRequest,
        members: list[Track],
        keeper_id: int,
    ) -> set[int]:
        if body.archive_track_ids is not None:
            return set(body.archive_track_ids)
        return {t.id for t in members if t.id != keeper_id}

    def _promote_keeper(
        self,
        track: Track,
        group: DuplicateGroup,
        settings: SettingsResponse,
    ) -> None:
        audio = self._audio_file(track)
        if audio is None:
            raise DuplicateResolveError("Keeper audio file is missing", status_code=409)

        ready_root = Path(settings.ready_folder).resolve()
        review_root = Path(settings.review_folder).resolve()
        if track.final_path:
            final = Path(track.final_path).resolve()
            if final.is_file() and (
                path_is_under_root(final, ready_root) or path_is_under_root(final, review_root)
            ):
                if path_is_under_root(final, review_root):
                    track.status = TrackStatus.REVIEW
                else:
                    track.status = TrackStatus.READY
                track.processing_path = clear_stale_processing_copy(
                    processing_path=track.processing_path,
                    final_path=track.final_path,
                )
                return

        processing_root = Path(settings.processing_folder)
        processing_root.mkdir(parents=True, exist_ok=True)
        dest = processing_root / audio.name
        if dest.exists() and track.processing_path != str(dest):
            dest = processing_root / f"{audio.stem}_{track.id}{audio.suffix}"

        from_duplicates = track.status == TrackStatus.DUPLICATE
        if audio.resolve() != dest.resolve():
            dest = move_into_destination(audio, dest)

        track.processing_path = str(dest)
        track.final_path = None
        track.status = TrackStatus.INGESTED
        if from_duplicates:
            track.tagged_at = None

        QueueService(self._db).enqueue_tag(track.source_path)

    def _archive_member(
        self,
        track: Track,
        group: DuplicateGroup,
        settings: SettingsResponse,
    ) -> None:
        audio = self._audio_file(track)
        if audio is None:
            track.status = TrackStatus.ARCHIVED
            track.processing_path = None
            return

        archive_root = Path(settings.archive_folder) / group.fingerprint_hash
        archive_root.mkdir(parents=True, exist_ok=True)
        dest = archive_root / audio.name
        if dest.exists() and track.final_path != str(dest):
            dest = archive_root / f"{audio.stem}_{track.id}{audio.suffix}"

        if audio.resolve() != dest.resolve():
            dest = move_into_destination(audio, dest)

        track.final_path = str(dest)
        track.processing_path = clear_stale_processing_copy(
            processing_path=track.processing_path,
            final_path=track.final_path,
        )
        track.status = TrackStatus.ARCHIVED

    def _members_for_group(self, group_id: int) -> list[Track]:
        rows = (
            self._db.execute(
                select(Track)
                .join(Fingerprint, Fingerprint.track_id == Track.id)
                .where(Fingerprint.duplicate_group_id == group_id)
            )
            .scalars()
            .all()
        )
        return list(rows)

    @staticmethod
    def _audio_file(track: Track) -> Path | None:
        for path_str in (track.final_path, track.processing_path):
            if not path_str:
                continue
            path = Path(path_str)
            if path.is_file():
                return path
        return None
