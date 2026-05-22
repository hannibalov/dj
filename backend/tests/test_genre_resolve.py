from pathlib import Path
from unittest.mock import patch

from app.metadata.genre_resolve import resolve_track_genres
from app.metadata.musicbrainz_lookup import RecordingGenreInfo


def test_resolve_track_genres_searches_by_artist_title_when_no_recording_id(
    tmp_path: Path,
) -> None:
    audio = tmp_path / "Firestarter - The Prodigy.mp3"
    audio.write_bytes(b"audio")

    with (
        patch(
            "app.metadata.genre_resolve.search_recording_id",
            return_value="mbid-prodigy-firestarter",
        ) as mock_search,
        patch(
            "app.metadata.genre_resolve.lookup_recording_genres",
            return_value=RecordingGenreInfo(
                genre="Electronic",
                subgenre="Big Beat",
                musicbrainz_recording_id="mbid-prodigy-firestarter",
            ),
        ),
    ):
        result = resolve_track_genres(
            audio_path=audio,
            musicbrainz_recording_id=None,
            artist="The Prodigy",
            title="Firestarter",
        )

    mock_search.assert_called_once_with("The Prodigy", "Firestarter")
    assert result.genre == "Electronic"
    assert result.subgenre == "Big Beat"
    assert result.musicbrainz_recording_id == "mbid-prodigy-firestarter"


def test_resolve_track_genres_skips_search_when_recording_id_provided(tmp_path: Path) -> None:
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"audio")

    with (
        patch("app.metadata.genre_resolve.search_recording_id") as mock_search,
        patch(
            "app.metadata.genre_resolve.lookup_recording_genres",
            return_value=RecordingGenreInfo("House", "Deep House", "mbid-1"),
        ),
    ):
        result = resolve_track_genres(
            audio_path=audio,
            musicbrainz_recording_id="mbid-1",
            artist="Artist",
            title="Title",
        )

    mock_search.assert_not_called()
    assert result.genre == "House"
