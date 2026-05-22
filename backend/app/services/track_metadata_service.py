"""Manual artist/title overrides written to file tags and the database."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.metadata.rename import build_library_filename
from app.metadata.tags import write_tags
from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.track import Track
from app.utils.audio_format import get_format_info
from app.services.fingerprint_service import FingerprintService
from app.services.notify import notify_pipeline_changed
from app.services.settings_service import SettingsService

logger = get_logger("TAGGER")


class TrackMetadataError(Exception):
    pass


class TrackMetadataService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def update_metadata(self, track_id: int, *, artist: str, title: str) -> Track:
        artist = artist.strip()
        title = title.strip()
        if not artist or not title:
            raise TrackMetadataError("Artist and title are required")

        track = self._db.get(Track, track_id)
        if track is None:
            raise TrackMetadataError(f"Track not found: {track_id}")

        audio_path = _resolve_writable_audio_path(track)
        if audio_path is None:
            raise TrackMetadataError("No audio file on disk to tag")

        write_tags(audio_path, artist=artist, title=title, album=track.album)

        settings = SettingsService(self._db).get_all()
        new_name = build_library_filename(
            artist=artist,
            title=title,
            mix=track.mix_version,
            extension=audio_path.suffix,
            template=settings.naming_template,
        )
        dest = audio_path.with_name(new_name)
        final_path = audio_path

        if dest.resolve() != audio_path.resolve():
            collision_track = _find_track_owning_path(self._db, dest)
            if collision_track is not None and collision_track.id != track.id:
                routed = self._route_on_fingerprint_collision(
                    track,
                    collision_track,
                    target_name=new_name,
                )
                if routed:
                    final_path = Path(track.final_path) if track.final_path else audio_path
                else:
                    dest = _unique_dest(dest, track.id)
                    audio_path.rename(dest)
                    _sync_track_paths(track, audio_path, dest)
                    final_path = dest
            elif dest.is_file():
                dest = _unique_dest(dest, track.id)
                audio_path.rename(dest)
                _sync_track_paths(track, audio_path, dest)
                final_path = dest
            else:
                audio_path.rename(dest)
                _sync_track_paths(track, audio_path, dest)
                final_path = dest

        if track.status != TrackStatus.DUPLICATE and self._reconcile_fingerprint_duplicate(
            track, target_name=new_name
        ):
            final_path = Path(track.final_path) if track.final_path else audio_path

        track.artist = artist
        track.title = title
        track.tagged_at = datetime.now(UTC)
        track.tag_confidence = 1.0
        track.needs_metadata_review = False
        self._db.commit()
        self._db.refresh(track)

        notify_pipeline_changed(f"Metadata updated: {artist} — {title}")
        logger.info(
            "track_metadata_updated",
            track_id=track_id,
            artist=artist,
            title=title,
            path=str(final_path),
        )
        return track

    def _route_on_fingerprint_collision(
        self,
        track: Track,
        other: Track,
        *,
        target_name: str,
    ) -> bool:
        fp_self = _fingerprint_for_track(self._db, track.id)
        fp_other = _fingerprint_for_track(self._db, other.id)
        if fp_self is None or fp_other is None:
            return False
        if fp_self.fingerprint_hash != fp_other.fingerprint_hash:
            return False

        FingerprintService(self._db).route_to_duplicates_folder(
            track,
            fp_self.fingerprint_hash,
            target_name=target_name,
        )
        logger.info(
            "track_metadata_duplicate_routed",
            track_id=track.id,
            other_track_id=other.id,
            fingerprint_hash=fp_self.fingerprint_hash[:12],
        )
        return True

    def _reconcile_fingerprint_duplicate(self, track: Track, *, target_name: str) -> bool:
        """After rename, demote this track if a same-format copy is already in ready/."""
        if track.status == TrackStatus.READY:
            return False

        fp = _fingerprint_for_track(self._db, track.id)
        if fp is None:
            return False

        others = (
            self._db.execute(
                select(Track)
                .join(Fingerprint, Fingerprint.track_id == Track.id)
                .where(
                    Fingerprint.fingerprint_hash == fp.fingerprint_hash,
                    Track.id != track.id,
                    Track.status != TrackStatus.ARCHIVED,
                )
            )
            .scalars()
            .all()
        )
        if not others:
            return False

        self_path = _resolve_writable_audio_path(track)
        if self_path is None:
            return False
        self_family = get_format_info(self_path).family

        for other in others:
            if other.status != TrackStatus.READY:
                continue
            other_path = _resolve_writable_audio_path(other)
            if other_path is None:
                continue
            if get_format_info(other_path).family != self_family:
                continue

            FingerprintService(self._db).route_to_duplicates_folder(
                track,
                fp.fingerprint_hash,
                target_name=target_name,
            )
            logger.info(
                "track_metadata_duplicate_reconciled",
                track_id=track.id,
                keeper_track_id=other.id,
                fingerprint_hash=fp.fingerprint_hash[:12],
            )
            return True
        return False


def _resolve_writable_audio_path(track: Track) -> Path | None:
    for path_str in (track.processing_path, track.final_path, track.source_path):
        if not path_str:
            continue
        path = Path(path_str)
        if path.is_file():
            return path
    return None


def _find_track_owning_path(db: Session, path: Path) -> Track | None:
    if not path.is_file():
        return None
    resolved = path.resolve()
    candidates = db.execute(
        select(Track).where(
            or_(Track.final_path.isnot(None), Track.processing_path.isnot(None))
        )
    ).scalars()
    for track in candidates:
        for path_str in (track.final_path, track.processing_path):
            if not path_str:
                continue
            candidate = Path(path_str)
            if candidate == path or candidate.resolve() == resolved:
                return track
    return None


def _fingerprint_for_track(db: Session, track_id: int) -> Fingerprint | None:
    return db.execute(
        select(Fingerprint).where(Fingerprint.track_id == track_id)
    ).scalar_one_or_none()


def _sync_track_paths(track: Track, old_path: Path, new_path: Path) -> None:
    old = str(old_path)
    new = str(new_path)
    if track.processing_path == old:
        track.processing_path = new
    if track.final_path == old:
        track.final_path = new


def _unique_dest(dest: Path, track_id: int) -> Path:
    if not dest.exists():
        return dest
    return dest.with_name(f"{dest.stem}_{track_id}{dest.suffix}")
