"""Manual artist/title overrides written to file tags and the database."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.metadata.genre import title_case_genre
from app.metadata.genre_resolve import apply_resolved_genres_to_file, resolve_track_genres
from app.metadata.rename import build_library_filename, normalize_track_credits
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

    def update_metadata(
        self,
        track_id: int,
        *,
        artist: str,
        title: str,
        genre: str | None = None,
        subgenre: str | None = None,
    ) -> Track:
        artist = artist.strip()
        title = title.strip()
        if not artist or not title:
            raise TrackMetadataError("Artist and title are required")

        track = self._db.get(Track, track_id)
        if track is None:
            raise TrackMetadataError(f"Track not found: {track_id}")

        old_genre = track.genre
        old_subgenre = track.subgenre
        genre = _normalize_genre_field(genre)
        subgenre = _normalize_genre_field(subgenre)
        genre_fields_changed = genre != old_genre or subgenre != old_subgenre

        artist, title, mix_version = normalize_track_credits(artist, title, track.mix_version)

        audio_path = _resolve_writable_audio_path(track)
        if audio_path is None:
            raise TrackMetadataError("No audio file on disk to tag")

        write_tags(audio_path, artist=artist, title=title, album=track.album)

        settings = SettingsService(self._db).get_all()
        new_name = build_library_filename(
            artist=artist,
            title=title,
            mix=mix_version,
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
        track.mix_version = mix_version
        track.genre = genre
        track.subgenre = subgenre
        track.tagged_at = datetime.now(UTC)
        track.tag_confidence = 1.0
        track.needs_metadata_review = False

        if genre_fields_changed:
            apply_resolved_genres_to_file(
                final_path,
                genre=track.genre,
                subgenre=track.subgenre,
                artist=track.artist,
                title=track.title,
                album=track.album,
            )
        else:
            self._resolve_genres_after_edit(track, final_path)

        self._db.commit()
        self._db.refresh(track)

        self._notify_song_duplicate_review()

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


    def _resolve_genres_after_edit(self, track: Track, audio_path: Path) -> None:
        """Re-fetch genre/subgenre from MusicBrainz after manual artist/title correction."""
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

        if genres.genre and not track.genre:
            track.genre = genres.genre
        if genres.subgenre and not track.subgenre:
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
            "track_genres_resolved_after_metadata_edit",
            track_id=track.id,
            genre=track.genre,
            subgenre=track.subgenre,
        )

    def _notify_song_duplicate_review(self) -> None:
        from app.services.song_duplicate_service import SongDuplicateService

        groups = SongDuplicateService(self._db).list_groups()
        if groups:
            notify_pipeline_changed(
                f"Same-song review: {len(groups)} group(s) need comparison"
            )


def _normalize_genre_field(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return title_case_genre(cleaned)


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
