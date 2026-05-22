from unittest.mock import MagicMock, patch

import httpx

from app.metadata.musicbrainz_lookup import RecordingSearchMatch, search_recording_id, search_recording_match


def test_search_recording_id_returns_first_match() -> None:
    payload = {
        "recordings": [
            {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "title": "Firestarter",
                "artist-credit": [{"name": "The Prodigy"}],
            },
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
        recording_id = search_recording_id("The Prodigy", "Firestarter")

    assert recording_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    mock_client.get.assert_called_once()
    call_kwargs = mock_client.get.call_args.kwargs
    assert "The Prodigy" in call_kwargs["params"]["query"]
    assert "Firestarter" in call_kwargs["params"]["query"]


def test_search_recording_match_picks_closest_duration() -> None:
    payload = {
        "recordings": [
            {
                "id": "short",
                "title": "Firestarter",
                "length": 180000,
                "artist-credit": [{"name": "The Prodigy"}],
            },
            {
                "id": "album-version",
                "title": "Firestarter",
                "length": 279000,
                "artist-credit": [{"name": "The Prodigy"}],
            },
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
        match = search_recording_match("The Prodigy", "Firestarter", duration_seconds=279.0)

    assert match is not None
    assert match.musicbrainz_recording_id == "album-version"
    assert match.artist == "The Prodigy"


def test_search_recording_id_returns_none_on_empty_results() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"recordings": []}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.get.return_value = mock_response

    with patch("app.metadata.musicbrainz_lookup.httpx.Client", return_value=mock_client):
        assert search_recording_id("Unknown", "Track") is None


def test_search_recording_id_returns_none_on_http_error() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.get.side_effect = httpx.HTTPError("network")

    with patch("app.metadata.musicbrainz_lookup.httpx.Client", return_value=mock_client):
        assert search_recording_id("Artist", "Title") is None
