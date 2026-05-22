"""MusicBrainz recording genres and community tags."""

from dataclasses import dataclass

import httpx

from app.logging import get_logger
from app.metadata.genre import title_case_genre

logger = get_logger("TAGGER")

MB_BASE = "https://musicbrainz.org/ws/2"
USER_AGENT = "dj-library-pipeline/0.1.0 (https://github.com/hannibalov/dj)"
REQUEST_TIMEOUT = 10.0


@dataclass(frozen=True)
class RecordingGenreInfo:
    genre: str | None
    subgenre: str | None
    musicbrainz_recording_id: str | None = None


def search_recording_id(artist: str, title: str) -> str | None:
    """Find a MusicBrainz recording ID from artist and title (no AcoustID required)."""
    artist = artist.strip()
    title = title.strip()
    if not artist or not title:
        return None

    query = f'artist:"{_lucene_escape(artist)}" AND recording:"{_lucene_escape(title)}"'
    url = f"{MB_BASE}/recording"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(
                url,
                params={"query": query, "fmt": "json", "limit": 3},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning(
            "musicbrainz_search_failed",
            artist=artist,
            title=title,
            error=str(exc),
        )
        return None
    except Exception as exc:
        logger.warning(
            "musicbrainz_search_error",
            artist=artist,
            title=title,
            error=str(exc),
        )
        return None

    recordings = data.get("recordings")
    if not isinstance(recordings, list) or not recordings:
        return None

    first = recordings[0]
    if not isinstance(first, dict):
        return None
    recording_id = first.get("id")
    return recording_id if isinstance(recording_id, str) and recording_id else None


def lookup_recording_genres(recording_id: str) -> RecordingGenreInfo:
    """Fetch top genre and a more specific subgenre tag from MusicBrainz."""
    if not recording_id:
        return RecordingGenreInfo(None, None)

    url = f"{MB_BASE}/recording/{recording_id}"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(
                url,
                params={"inc": "genres+tags", "fmt": "json"},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("musicbrainz_lookup_failed", recording_id=recording_id, error=str(exc))
        return RecordingGenreInfo(None, None, recording_id)
    except Exception as exc:
        logger.warning("musicbrainz_lookup_error", recording_id=recording_id, error=str(exc))
        return RecordingGenreInfo(None, None, recording_id)

    parsed = _parse_recording_genres(data)
    return RecordingGenreInfo(
        genre=parsed.genre,
        subgenre=parsed.subgenre,
        musicbrainz_recording_id=recording_id,
    )


def _parse_recording_genres(data: dict[str, object]) -> RecordingGenreInfo:
    genres = _sorted_names(data.get("genres"))
    tags = _sorted_names(data.get("tags"))

    genre = title_case_genre(genres[0]) if genres else None
    if genre is None and tags:
        genre = title_case_genre(tags[0])

    subgenre = _pick_subgenre(genre, genres, tags)
    return RecordingGenreInfo(genre=genre, subgenre=subgenre)


def _sorted_names(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    scored: list[tuple[int, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        count = item.get("count")
        score = int(count) if isinstance(count, int) else 0
        scored.append((score, name.strip()))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [name for _, name in scored]


def _pick_subgenre(genre: str | None, genres: list[str], tags: list[str]) -> str | None:
    genre_fold = genre.casefold() if genre else None

    for name in tags:
        folded = name.casefold()
        if genre_fold and folded == genre_fold:
            continue
        if genre_fold and folded.startswith(f"{genre_fold} "):
            return title_case_genre(name)
        if genre_fold and genre_fold in folded and folded != genre_fold:
            return title_case_genre(name)

    for name in genres[1:]:
        if genre_fold and name.casefold() == genre_fold:
            continue
        return title_case_genre(name)

    for name in tags:
        if genre_fold and name.casefold() == genre_fold:
            continue
        return title_case_genre(name)

    return None


def _lucene_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
