"""Backfill missing genre/subgenre for tagged tracks via MusicBrainz."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.metadata.genre_resolve import apply_resolved_genres_to_file, resolve_track_genres
from app.models.enums import TrackStatus
from app.models.track import Track
from app.services.notify import notify_pipeline_changed

logger = get_logger("TAGGER")


@dataclass(frozen=True)
class GenreBackfillResult:
    status: str
    enriched: int
    skipped: int


class GenreBackfillService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def backfill_missing_genres(self) -> GenreBackfillResult:
        """
        Resolve genre/subgenre for tracks that already have artist and title.

        Runs inline (no worker job). Respects MusicBrainz rate limits via lookup layer.
        """
        tracks = (
            self._db.execute(
                select(Track).where(
                    Track.artist.isnot(None),
                    Track.title.isnot(None),
                    Track.artist != "",
                    Track.title != "",
                    or_(Track.genre.is_(None), Track.subgenre.is_(None)),
                    Track.status.notin_(
                        (
                            TrackStatus.DUPLICATE,
                            TrackStatus.ARCHIVED,
                            TrackStatus.FAILED,
                        )
                    ),
                )
            )
            .scalars()
            .all()
        )

        enriched = 0
        skipped = 0
        for track in tracks:
            audio_path = _resolve_audio_path(track)
            if audio_path is None:
                skipped += 1
                continue

            genres = resolve_track_genres(
                audio_path=audio_path,
                musicbrainz_recording_id=track.musicbrainz_recording_id,
                artist=track.artist,
                title=track.title,
            )
            if not genres.genre and not genres.subgenre:
                skipped += 1
                continue

            if genres.genre and not track.genre:
                track.genre = genres.genre
            if genres.subgenre and not track.subgenre:
                track.subgenre = genres.subgenre
            if genres.musicbrainz_recording_id and not track.musicbrainz_recording_id:
                track.musicbrainz_recording_id = genres.musicbrainz_recording_id

            apply_resolved_genres_to_file(
                audio_path,
                genre=track.genre,
                subgenre=track.subgenre,
                artist=track.artist,
                title=track.title,
                album=track.album,
            )
            enriched += 1
            logger.info(
                "genre_backfill_enriched",
                track_id=track.id,
                artist=track.artist,
                title=track.title,
                genre=track.genre,
                subgenre=track.subgenre,
            )

        if enriched:
            self._db.commit()
            notify_pipeline_changed(
                f"Genre backfill: enriched {enriched}, skipped {skipped}"
            )
        else:
            self._db.commit()

        return GenreBackfillResult(status="ok", enriched=enriched, skipped=skipped)


def _resolve_audio_path(track: Track) -> Path | None:
    for path_str in (track.final_path, track.processing_path, track.source_path):
        if not path_str:
            continue
        path = Path(path_str)
        if path.is_file():
            return path
    return None
