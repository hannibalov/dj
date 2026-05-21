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
