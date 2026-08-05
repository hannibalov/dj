from collections.abc import Mapping
from unittest.mock import MagicMock, patch

import httpx

from app.metadata.musicbrainz_lookup import lookup_recording_genres


def test_lookup_recording_genres_parses_response() -> None:
    payload = {
        "genres": [{"name": "house", "count": 4}],
        "tags": [
            {"name": "house", "count": 4},
            {"name": "deep house", "count": 2},
        ],
    }
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = payload

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.get.return_value = mock_response

    with patch("app.metadata.musicbrainz_lookup.httpx.Client", return_value=mock_client):
        info = lookup_recording_genres("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    assert info.genre == "House"
    assert info.subgenre == "Deep House"


def test_lookup_recording_genres_returns_empty_on_http_error() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.get.side_effect = httpx.HTTPError("network")

    with patch("app.metadata.musicbrainz_lookup.httpx.Client", return_value=mock_client):
        info = lookup_recording_genres("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    assert info.genre is None
    assert info.subgenre is None


def test_lookup_recording_genres_falls_back_to_release() -> None:
    recording_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    release_id = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    recording_payload = {
        "genres": [],
        "tags": [],
        "releases": [{"id": release_id}],
        "artist-credit": [{"artist": {"id": "artist-1", "name": "Artist"}}],
    }
    release_payload = {
        "genres": [{"name": "electronic", "count": 3}],
        "tags": [{"name": "techno", "count": 2}],
    }

    def fake_mb_get(url: str, params: Mapping[str, str | int]) -> Mapping[str, object] | None:
        if url.endswith(f"/recording/{recording_id}"):
            return recording_payload
        if url.endswith(f"/release/{release_id}"):
            return release_payload
        return None

    with patch("app.metadata.musicbrainz_lookup._mb_get", side_effect=fake_mb_get):
        info = lookup_recording_genres(recording_id)

    assert info.genre == "Electronic"
    assert info.subgenre == "Techno"


def test_lookup_recording_genres_falls_back_to_artist() -> None:
    recording_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    artist_id = "c3d4e5f6-a7b8-9012-cdef-123456789012"
    recording_payload = {
        "genres": [],
        "tags": [],
        "releases": [],
        "artist-credit": [{"artist": {"id": artist_id, "name": "Artist"}}],
    }
    artist_payload = {
        "genres": [{"name": "house", "count": 5}],
        "tags": [{"name": "deep house", "count": 2}],
    }

    def fake_mb_get(url: str, params: Mapping[str, str | int]) -> Mapping[str, object] | None:
        if url.endswith(f"/recording/{recording_id}"):
            return recording_payload
        if url.endswith(f"/artist/{artist_id}"):
            return artist_payload
        return None

    with patch("app.metadata.musicbrainz_lookup._mb_get", side_effect=fake_mb_get):
        info = lookup_recording_genres(recording_id)

    assert info.genre == "House"
    assert info.subgenre == "Deep House"
