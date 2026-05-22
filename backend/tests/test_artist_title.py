from pathlib import Path
from unittest.mock import patch

from app.metadata.artist_title import embedded_tags_swapped, resolve_artist_title
from app.metadata.matcher import match_track_metadata
from app.metadata.normalize import normalize_embedded_tags
from app.metadata.rename import build_library_filename
from app.metadata.tags import parse_filename_metadata
from app.metadata.types import FileTags


def test_resolve_ambiguous_single_word_pair_defaults_artist_first() -> None:
    """Without tags, prefer Artist - Title; MusicBrainz disambiguation fixes Title - Artist files."""
    artist, title = resolve_artist_title("CamelPhat", "Cola")
    assert artist == "CamelPhat"
    assert title == "Cola"


def test_resolve_artist_title_multiword() -> None:
    artist, title = resolve_artist_title("Jan Blomqvist", "The Space In Between")
    assert artist == "Jan Blomqvist"
    assert title == "The Space In Between"


def test_resolve_uses_embedded_artist_on_right() -> None:
    embedded = FileTags(artist="CamelPhat", title="Cola", album=None)
    artist, title = resolve_artist_title("CamelPhat", "Cola", embedded)
    assert artist == "CamelPhat"
    assert title == "Cola"


def test_normalize_youtube_channel_tags() -> None:
    normalized = normalize_embedded_tags(
        "Armada Music TV",
        "Jan Blomqvist - The Space In Between (Official Music Video)",
        filename=FileTags("Jan Blomqvist", "The Space In Between", None),
    )
    assert normalized.artist == "Jan Blomqvist"
    assert normalized.title == "The Space In Between"


def test_parse_filename_artist_first(tmp_path: Path) -> None:
    path = tmp_path / "CamelPhat - Cola.mp3"
    path.write_bytes(b"fake")
    parsed = parse_filename_metadata(path)
    assert parsed.artist == "CamelPhat"
    assert parsed.title == "Cola"


def test_build_library_filename_wonderwall() -> None:
    name = build_library_filename(
        artist="Oasis",
        title="Wonderwall",
        extension=".mp3",
    )
    assert name == "Wonderwall - Oasis (Original Mix).mp3"
    assert "Armada" not in name


def test_build_library_filename_jan_blomqvist() -> None:
    name = build_library_filename(
        artist="Jan Blomqvist",
        title="The Space In Between",
        extension=".mp3",
    )
    assert name == "The Space In Between - Jan Blomqvist (Original Mix).mp3"
    assert "Armada" not in name
    assert "Official Music Video" not in name


def test_matcher_prefers_musicbrainz_over_flipped_filename(tmp_path: Path) -> None:
    path = tmp_path / "Wonderwall - Oasis.mp3"
    path.write_bytes(b"fake")

    mb_hit = __import__(
        "app.metadata.musicbrainz_lookup", fromlist=["RecordingSearchMatch"]
    ).RecordingSearchMatch(
        artist="Oasis",
        title="Wonderwall",
        musicbrainz_recording_id="mbid-wonderwall",
        length_ms=258000,
    )

    with patch(
        "app.metadata.matcher.search_recording_best",
        return_value=mb_hit,
    ):
        match = match_track_metadata(
            path,
            raw_fingerprint=None,
            duration_seconds=258.0,
            acoustid_api_key=None,
            confidence_threshold=0.5,
        )

    assert match is not None
    assert match.artist == "Oasis"
    assert match.title == "Wonderwall"
    assert match.source == "musicbrainz"


def test_embedded_tags_swapped_detection() -> None:
    embedded = FileTags("Wonderwall", "Oasis", None)
    resolved = FileTags("Oasis", "Wonderwall", None)
    assert embedded_tags_swapped(embedded, resolved) is True
