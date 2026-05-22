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


@dataclass(frozen=True)
class RecordingSearchMatch:
    artist: str
    title: str
    musicbrainz_recording_id: str
    length_ms: int | None = None


def search_recording_id(artist: str, title: str) -> str | None:
    """Find a MusicBrainz recording ID from artist and title (no AcoustID required)."""
    match = search_recording_match(artist, title)
    return match.musicbrainz_recording_id if match else None


def search_recording_match(
    artist: str,
    title: str,
    *,
    duration_seconds: float | None = None,
) -> RecordingSearchMatch | None:
    """Search MusicBrainz recordings by artist and title parsed from the filename."""
    artist = artist.strip()
    title = title.strip()
    if not artist or not title:
        return None

    query = f'artist:"{_lucene_escape(artist)}" AND recording:"{_lucene_escape(title)}"'
    recordings = _search_recordings(query)
    if not recordings:
        return None

    picked = _pick_best_recording(recordings, duration_seconds=duration_seconds)
    return _parse_recording_match(picked) if picked else None


def _search_recordings(query: str, *, limit: int = 5) -> list[dict[str, object]]:
    url = f"{MB_BASE}/recording"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(
                url,
                params={"query": query, "fmt": "json", "limit": limit},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("musicbrainz_search_failed", query=query, error=str(exc))
        return []
    except Exception as exc:
        logger.warning("musicbrainz_search_error", query=query, error=str(exc))
        return []

    recordings = data.get("recordings")
    if not isinstance(recordings, list):
        return []
    return [item for item in recordings if isinstance(item, dict)]


def _pick_best_recording(
    recordings: list[dict[str, object]],
    *,
    duration_seconds: float | None,
) -> dict[str, object] | None:
    if not recordings:
        return None
    if duration_seconds is None:
        return recordings[0]

    target_ms = duration_seconds * 1000
    best: dict[str, object] | None = None
    best_delta = float("inf")
    for recording in recordings:
        length = recording.get("length")
        if not isinstance(length, int):
            continue
        delta = abs(length - target_ms)
        if delta < best_delta:
            best = recording
            best_delta = delta

    return best if best is not None else recordings[0]


def _parse_recording_match(recording: dict[str, object]) -> RecordingSearchMatch | None:
    recording_id = recording.get("id")
    title = recording.get("title")
    if not isinstance(recording_id, str) or not recording_id:
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    artist = _artist_from_recording(recording)
    if not artist:
        return None

    length = recording.get("length")
    length_ms = length if isinstance(length, int) else None
    return RecordingSearchMatch(
        artist=artist,
        title=title.strip(),
        musicbrainz_recording_id=recording_id,
        length_ms=length_ms,
    )


def _artist_from_recording(recording: dict[str, object]) -> str | None:
    credits = recording.get("artist-credit")
    if not isinstance(credits, list):
        return None

    parts: list[str] = []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        name = credit.get("name")
        if isinstance(name, str) and name.strip():
            parts.append(name.strip())
            continue
        artist = credit.get("artist")
        if isinstance(artist, dict):
            artist_name = artist.get("name")
            if isinstance(artist_name, str) and artist_name.strip():
                parts.append(artist_name.strip())

    if not parts:
        return None
    return ", ".join(parts)


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
