from unittest.mock import patch

from app.metadata.musicbrainz_lookup import RecordingSearchMatch, search_recording_best


def test_search_recording_best_picks_correct_ordering() -> None:
    forward = RecordingSearchMatch(
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-1",
        length_ms=279000,
    )
    swapped = RecordingSearchMatch(
        artist="Firestarter",
        title="The Prodigy",
        musicbrainz_recording_id="mbid-wrong",
        length_ms=120000,
    )

    with patch(
        "app.metadata.musicbrainz_lookup.search_recording_match",
        side_effect=[swapped, forward],
    ):
        hit = search_recording_best(
            "Firestarter",
            "The Prodigy",
            duration_seconds=279.0,
        )

    assert hit is not None
    assert hit.artist == "The Prodigy"
    assert hit.title == "Firestarter"
    assert hit.musicbrainz_recording_id == "mbid-1"
