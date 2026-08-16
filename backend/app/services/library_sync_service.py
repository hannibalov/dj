"""Reconcile SQLite track rows with audio files across all configured folders."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.metadata.known_artists import load_known_artists
from app.metadata.normalize import names_align
from app.metadata.tags import parse_filename_metadata
from app.models.enums import TrackStatus
from app.models.track import Track
from app.schemas.settings import SettingsResponse
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.utils.audio_extensions import is_audio_file
from app.utils.workspace_files import path_is_under_root


@dataclass(frozen=True)
class LibrarySyncResult:
    status: str
    enqueued: int
    skipped: int
    paths_repaired: int
    metadata_updated: int
    missing_files: int
    orphan_files: int


class LibrarySyncService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def sync_library(self) -> LibrarySyncResult:
        settings = SettingsService(self._db).get_all()
        known_artists = load_known_artists(self._db)
        folder_roots = self._library_roots(settings)
        disk_files = self._scan_audio_files(folder_roots)
        files_by_name = self._index_by_name(disk_files)

        tracks = self._db.execute(select(Track)).scalars().all()
        linked_paths = self._linked_paths(tracks)

        paths_repaired = 0
        metadata_updated = 0
        missing_files = 0

        for track in tracks:
            if self._repair_track_paths(track, files_by_name, folder_roots):
                paths_repaired += 1
            if not self._track_has_file(track):
                if track.status not in (TrackStatus.FAILED, TrackStatus.QUEUED):
                    track.status = TrackStatus.FAILED
                missing_files += 1
                continue
            if self._sync_metadata_from_file(track, known_artists):
                metadata_updated += 1

        enqueued = 0
        skipped = 0
        orphan_files = 0
        watch_root = Path(settings.watch_folder)

        for path in disk_files:
            resolved = path.resolve()
            if resolved in linked_paths:
                continue
            if path_is_under_root(path, watch_root):
                result = QueueService(self._db).enqueue_ingest(str(path))
                if result.enqueued:
                    enqueued += 1
                else:
                    skipped += 1
            else:
                orphan_files += 1

        self._db.commit()
        return LibrarySyncResult(
            status="ok",
            enqueued=enqueued,
            skipped=skipped,
            paths_repaired=paths_repaired,
            metadata_updated=metadata_updated,
            missing_files=missing_files,
            orphan_files=orphan_files,
        )

    @staticmethod
    def _library_roots(
        settings: SettingsResponse,
    ) -> list[tuple[Path, frozenset[TrackStatus] | None]]:
        return [
            (Path(settings.watch_folder), None),
            (Path(settings.incoming_folder), None),
            (
                Path(settings.processing_folder),
                frozenset({TrackStatus.INGESTED, TrackStatus.PROCESSING}),
            ),
            (Path(settings.ready_folder), frozenset({TrackStatus.READY})),
            (Path(settings.review_folder), frozenset({TrackStatus.REVIEW})),
            (Path(settings.duplicates_folder), frozenset({TrackStatus.DUPLICATE})),
            (Path(settings.archive_folder), frozenset({TrackStatus.ARCHIVED})),
            (Path(settings.failed_folder), frozenset({TrackStatus.FAILED})),
        ]

    @staticmethod
    def _scan_audio_files(
        folder_roots: list[tuple[Path, frozenset[TrackStatus] | None]],
    ) -> list[Path]:
        files: list[Path] = []
        seen: set[Path] = set()
        for root, _ in folder_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or not is_audio_file(path):
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                files.append(path)
        return files

    @staticmethod
    def _index_by_name(paths: list[Path]) -> dict[str, list[Path]]:
        by_name: dict[str, list[Path]] = {}
        for path in paths:
            by_name.setdefault(path.name, []).append(path)
        return by_name

    @staticmethod
    def _linked_paths(tracks: Sequence[Track]) -> set[Path]:
        linked: set[Path] = set()
        for track in tracks:
            for path_str in (track.source_path, track.processing_path, track.final_path):
                if not path_str:
                    continue
                path = Path(path_str)
                if path.exists():
                    linked.add(path.resolve())
        return linked

    def _repair_track_paths(
        self,
        track: Track,
        files_by_name: dict[str, list[Path]],
        folder_roots: list[tuple[Path, frozenset[TrackStatus] | None]],
    ) -> bool:
        changed = False
        if track.final_path and not Path(track.final_path).is_file():
            repaired = self._find_replacement(
                Path(track.final_path).name,
                files_by_name,
                folder_roots,
                preferred_statuses=self._final_path_statuses(track.status),
            )
            if repaired is not None:
                track.final_path = str(repaired)
                changed = True

        if track.processing_path and not Path(track.processing_path).is_file():
            repaired = self._find_replacement(
                Path(track.processing_path).name,
                files_by_name,
                folder_roots,
                preferred_statuses=frozenset({TrackStatus.INGESTED, TrackStatus.PROCESSING}),
            )
            if repaired is not None:
                track.processing_path = str(repaired)
                changed = True
        return changed

    @staticmethod
    def _final_path_statuses(status: TrackStatus) -> frozenset[TrackStatus]:
        if status == TrackStatus.REVIEW:
            return frozenset({TrackStatus.REVIEW})
        if status == TrackStatus.DUPLICATE:
            return frozenset({TrackStatus.DUPLICATE})
        if status == TrackStatus.ARCHIVED:
            return frozenset({TrackStatus.ARCHIVED})
        if status == TrackStatus.FAILED:
            return frozenset({TrackStatus.FAILED})
        return frozenset({TrackStatus.READY, TrackStatus.REVIEW})

    @staticmethod
    def _find_replacement(
        basename: str,
        files_by_name: dict[str, list[Path]],
        folder_roots: list[tuple[Path, frozenset[TrackStatus] | None]],
        *,
        preferred_statuses: frozenset[TrackStatus],
    ) -> Path | None:
        candidates = files_by_name.get(basename, [])
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        preferred_roots = [
            root
            for root, statuses in folder_roots
            if statuses is None or statuses.intersection(preferred_statuses)
        ]
        for root in preferred_roots:
            for candidate in candidates:
                if path_is_under_root(candidate, root):
                    return candidate
        return candidates[0]

    @staticmethod
    def _track_has_file(track: Track) -> bool:
        for path_str in (track.processing_path, track.final_path, track.source_path):
            if path_str and Path(path_str).is_file():
                return True
        return False

    @staticmethod
    def _sync_metadata_from_file(track: Track, known_artists: frozenset[str]) -> bool:
        audio_path = LibrarySyncService._writable_audio_path(track)
        if audio_path is None:
            return False

        parsed = parse_filename_metadata(audio_path, known_artists=known_artists)
        if not parsed.artist or not parsed.title:
            return False

        current_artist = (track.artist or "").strip()
        current_title = (track.title or "").strip()
        if (
            current_artist
            and current_title
            and names_align(current_artist, parsed.artist)
            and names_align(current_title, parsed.title)
        ):
            return False

        if (
            current_artist == parsed.artist
            and current_title == parsed.title
            and current_artist
            and current_title
        ):
            return False

        track.artist = parsed.artist
        track.title = parsed.title
        return True

    @staticmethod
    def _writable_audio_path(track: Track) -> Path | None:
        for path_str in (track.final_path, track.processing_path, track.source_path):
            if not path_str:
                continue
            path = Path(path_str)
            if path.is_file():
                return path
        return None

    def cleanup_missing_tracks(self) -> int:
        """Delete tracks from the database that no longer have any existing audio file.

        Returns the number of deleted track rows.
        """
        tracks = self._db.execute(select(Track)).scalars().all()
        deleted = 0
        for track in tracks:
            if not self._track_has_file(track):
                try:
                    self._db.delete(track)
                    deleted += 1
                except Exception:
                    # best-effort: continue on errors
                    continue
        self._db.commit()
        return deleted
