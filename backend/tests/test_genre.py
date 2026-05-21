from app.metadata.genre import parse_embedded_genre, title_case_genre
from app.metadata.musicbrainz_lookup import _parse_recording_genres


def test_parse_embedded_genre_splits_compound() -> None:
    genre, subgenre = parse_embedded_genre("Electronic; Techno")
    assert genre == "Electronic"
    assert subgenre == "Techno"


def test_parse_embedded_genre_single() -> None:
    genre, subgenre = parse_embedded_genre("techno")
    assert genre == "Techno"
    assert subgenre is None


def test_title_case_genre_all_caps() -> None:
    assert title_case_genre("DRUM AND BASS") == "Drum And Bass"


def test_musicbrainz_parse_genre_and_subgenre() -> None:
    data = {
        "genres": [{"name": "techno", "count": 10}],
        "tags": [
            {"name": "techno", "count": 10},
            {"name": "minimal techno", "count": 6},
        ],
    }
    info = _parse_recording_genres(data)
    assert info.genre == "Techno"
    assert info.subgenre == "Minimal Techno"
