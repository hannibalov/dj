from pathlib import Path
from unittest.mock import patch

from app.metadata.matcher import match_track_metadata
from app.metadata.types import FileTags


def test_reprocess_ignores_stale_embedded_tags(tmp_path: Path) -> None:
    audio = tmp_path / "processing" / "track_1.mp3"
    watch = tmp_path / "watch" / "Jan Blomqvist - The Space In Between.mp3"
    audio.parent.mkdir(parents=True)
    watch.parent.mkdir(parents=True)
    audio.write_bytes(b"x")
    watch.write_bytes(b"x")

    wrong = FileTags(artist="Wrong Artist", title="Wrong Title", album=None)
    empty = FileTags(artist=None, title=None, album=None)

    with (
        patch("app.metadata.matcher.read_tags", return_value=wrong),
        patch("app.metadata.tags.read_tags", return_value=empty),
    ):
        match = match_track_metadata(
            audio,
            raw_fingerprint=None,
            duration_seconds=None,
            acoustid_api_key=None,
            confidence_threshold=0.5,
            reprocess=True,
            filename_hint_path=watch,
        )

    assert match is not None
    assert match.artist == "Jan Blomqvist"
    assert "Space In Between" in match.title
    assert match.source == "filename"


def test_reprocess_prefers_watch_filename_over_generic_processing_name(tmp_path: Path) -> None:
    audio = tmp_path / "processing" / "track_99.mp3"
    watch = tmp_path / "watch" / "Jan Blomqvist - The Space In Between.mp3"
    audio.parent.mkdir(parents=True)
    watch.parent.mkdir(parents=True)
    audio.write_bytes(b"x")
    watch.write_bytes(b"x")

    empty = FileTags(artist=None, title=None, album=None)

    with (
        patch("app.metadata.matcher.read_tags", return_value=empty),
        patch("app.metadata.tags.read_tags", return_value=empty),
    ):
        match = match_track_metadata(
            audio,
            raw_fingerprint=None,
            duration_seconds=None,
            acoustid_api_key=None,
            confidence_threshold=0.5,
            reprocess=True,
            filename_hint_path=watch,
        )

    assert match is not None
    assert match.artist == "Jan Blomqvist"
    assert "Space In Between" in match.title
