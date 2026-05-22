from pathlib import Path
from unittest.mock import patch

from app.metadata.matcher import match_track_metadata
from app.metadata.musicbrainz_lookup import RecordingSearchMatch
from app.metadata.types import FileTags


def test_low_confidence_filename_match_uses_musicbrainz_search(tmp_path: Path) -> None:
    audio = tmp_path / "processing" / "Firestarter - The Prodigy.mp3"
    watch = tmp_path / "watch" / "Firestarter - The Prodigy.mp3"
    audio.parent.mkdir(parents=True)
    watch.parent.mkdir(parents=True)
    audio.write_bytes(b"x")
    watch.write_bytes(b"x")

    empty = FileTags(artist=None, title=None, album=None)
    mb_hit = RecordingSearchMatch(
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-firestarter",
        length_ms=279000,
    )

    with (
        patch("app.metadata.matcher.read_tags", return_value=empty),
        patch("app.metadata.tags.read_tags", return_value=empty),
        patch("app.metadata.matcher.search_recording_best", return_value=mb_hit) as mock_search,
    ):
        match = match_track_metadata(
            audio,
            raw_fingerprint=None,
            duration_seconds=279.0,
            acoustid_api_key=None,
            confidence_threshold=0.85,
            reprocess=True,
            filename_hint_path=watch,
        )

    assert match is not None
    assert match.source == "musicbrainz"
    assert match.artist == "The Prodigy"
    assert match.title == "Firestarter"
    assert match.musicbrainz_recording_id == "mbid-firestarter"
    assert match.confidence >= 0.9
    mock_search.assert_called_once_with(
        "Firestarter",
        "The Prodigy",
        duration_seconds=279.0,
    )


def test_high_confidence_acoustid_skips_musicbrainz_search(tmp_path: Path) -> None:
    audio = tmp_path / "watch" / "song.mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"x")

    with (
        patch(
            "app.metadata.matcher.lookup_by_fingerprint",
            return_value=__import__(
                "app.metadata.acoustid_lookup", fromlist=["AcoustIdMatch"]
            ).AcoustIdMatch(
                artist="Artist",
                title="Title",
                album=None,
                mix_version=None,
                recording_id="mbid-1",
                score=0.95,
            ),
        ),
        patch("app.metadata.matcher.search_recording_best") as mock_search,
    ):
        match = match_track_metadata(
            audio,
            raw_fingerprint="fp",
            duration_seconds=200.0,
            acoustid_api_key="key",
            confidence_threshold=0.85,
        )

    assert match is not None
    assert match.source == "acoustid"
    mock_search.assert_not_called()
