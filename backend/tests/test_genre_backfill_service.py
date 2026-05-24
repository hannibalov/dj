from pathlib import Path
from unittest.mock import patch

from app.metadata.musicbrainz_lookup import RecordingGenreInfo
from app.models.enums import TrackStatus
from app.models.track import Track
from app.services.genre_backfill_service import GenreBackfillService


def test_backfill_missing_genres_enriches_tracks(db_session, tmp_path: Path) -> None:
    audio = tmp_path / "ready" / "Song - Artist (Original Mix).mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"audio")

    track = Track(
        source_path=str(tmp_path / "watch" / audio.name),
        final_path=str(audio),
        status=TrackStatus.READY,
        artist="Artist",
        title="Song",
        genre=None,
        subgenre=None,
    )
    db_session.add(track)
    db_session.commit()

    with (
        patch(
            "app.services.genre_backfill_service.resolve_track_genres",
            return_value=RecordingGenreInfo(
                genre="House",
                subgenre="Deep House",
                musicbrainz_recording_id="mbid-1",
            ),
        ),
        patch("app.services.genre_backfill_service.apply_resolved_genres_to_file") as mock_apply,
        patch("app.services.genre_backfill_service.notify_pipeline_changed"),
    ):
        result = GenreBackfillService(db_session).backfill_missing_genres()

    assert result.enriched == 1
    assert result.skipped == 0
    db_session.refresh(track)
    assert track.genre == "House"
    assert track.subgenre == "Deep House"
    assert track.musicbrainz_recording_id == "mbid-1"
    mock_apply.assert_called_once()


def test_backfill_missing_genres_skips_when_no_genres_found(db_session, tmp_path: Path) -> None:
    audio = tmp_path / "ready" / "Song - Artist (Original Mix).mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"audio")

    track = Track(
        source_path=str(tmp_path / "watch" / audio.name),
        final_path=str(audio),
        status=TrackStatus.READY,
        artist="Artist",
        title="Song",
    )
    db_session.add(track)
    db_session.commit()

    with (
        patch(
            "app.services.genre_backfill_service.resolve_track_genres",
            return_value=RecordingGenreInfo(None, None, None),
        ),
        patch("app.services.genre_backfill_service.apply_resolved_genres_to_file") as mock_apply,
        patch("app.services.genre_backfill_service.notify_pipeline_changed"),
    ):
        result = GenreBackfillService(db_session).backfill_missing_genres()

    assert result.enriched == 0
    assert result.skipped == 1
    mock_apply.assert_not_called()


def test_backfill_missing_genres_fills_subgenre_only(db_session, tmp_path: Path) -> None:
    audio = tmp_path / "ready" / "Song - Artist (Original Mix).mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"audio")

    track = Track(
        source_path=str(tmp_path / "watch" / audio.name),
        final_path=str(audio),
        status=TrackStatus.READY,
        artist="Artist",
        title="Song",
        genre="House",
        subgenre=None,
    )
    db_session.add(track)
    db_session.commit()

    with (
        patch(
            "app.services.genre_backfill_service.resolve_track_genres",
            return_value=RecordingGenreInfo(
                genre="House",
                subgenre="Deep House",
                musicbrainz_recording_id="mbid-1",
            ),
        ),
        patch("app.services.genre_backfill_service.apply_resolved_genres_to_file"),
        patch("app.services.genre_backfill_service.notify_pipeline_changed"),
    ):
        result = GenreBackfillService(db_session).backfill_missing_genres()

    assert result.enriched == 1
    db_session.refresh(track)
    assert track.genre == "House"
    assert track.subgenre == "Deep House"
