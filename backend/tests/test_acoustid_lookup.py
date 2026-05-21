from unittest.mock import MagicMock, patch

from app.metadata.acoustid_lookup import lookup_by_fingerprint


def test_lookup_uses_parse_lookup_result_not_raw_json_keys() -> None:
    """Regression: list(lookup()) used dict keys; unpack raised ValueError."""
    fake_response = {
        "status": "ok",
        "results": [
            {
                "score": 0.95,
                "recordings": [
                    {
                        "id": "mbid-1",
                        "title": "Wegue Wegue",
                        "artists": [{"name": "Pongo", "joinphrase": ""}],
                    }
                ],
            }
        ],
    }
    parsed = [(0.95, "mbid-1", "Wegue Wegue", "Pongo")]

    mock_acoustid = MagicMock()
    mock_acoustid.lookup.return_value = fake_response
    mock_acoustid.parse_lookup_result.return_value = iter(parsed)
    mock_acoustid.AcoustidError = Exception

    with patch("app.metadata.acoustid_lookup.acoustid", mock_acoustid):
        match = lookup_by_fingerprint("key", "fp-data", 200.0)

    assert match is not None
    assert match.artist == "Pongo"
    assert match.title == "Wegue Wegue"
    mock_acoustid.parse_lookup_result.assert_called_once_with(fake_response)


def test_lookup_returns_none_when_no_recordings() -> None:
    mock_acoustid = MagicMock()
    mock_acoustid.lookup.return_value = {"status": "ok", "results": []}
    mock_acoustid.parse_lookup_result.return_value = iter([])
    mock_acoustid.AcoustidError = Exception

    with patch("app.metadata.acoustid_lookup.acoustid", mock_acoustid):
        assert lookup_by_fingerprint("key", "fp", 100.0) is None
