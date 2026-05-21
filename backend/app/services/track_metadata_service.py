"""Manual artist/title overrides written to file tags and the database."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.logging import get_logger
from app.metadata.rename import build_library_filename
from app.metadata.tags import write_tags
from app.models.track import Track
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
        if dest != audio_path:
            dest = _unique_dest(dest, track.id)
            audio_path.rename(dest)
            if track.processing_path == str(audio_path):
                track.processing_path = str(dest)
            elif track.final_path == str(audio_path):
                track.final_path = str(dest)

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
            path=str(dest if dest != audio_path else audio_path),
        )
        return track


def _resolve_writable_audio_path(track: Track) -> Path | None:
    for path_str in (track.processing_path, track.final_path, track.source_path):
        if not path_str:
            continue
        path = Path(path_str)
        if path.is_file():
            return path
    return None


def _unique_dest(dest: Path, track_id: int) -> Path:
    if not dest.exists():
        return dest
    return dest.with_name(f"{dest.stem}_{track_id}{dest.suffix}")
