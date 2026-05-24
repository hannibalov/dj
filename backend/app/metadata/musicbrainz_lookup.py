"""MusicBrainz recording genres and community tags."""

import time
from dataclasses import dataclass

import httpx

from app.logging import get_logger
from app.metadata.genre import title_case_genre
from app.metadata.rename import normalize_track_credits

logger = get_logger("TAGGER")

MB_BASE = "https://musicbrainz.org/ws/2"
USER_AGENT = "dj-library-pipeline/0.1.0 (https://github.com/hannibalov/dj)"
REQUEST_TIMEOUT = 10.0
_MB_MIN_INTERVAL = 1.1
_mb_last_request_at = 0.0


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
    """Search MusicBrainz recordings by artist and title."""
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


def search_recording_best(
    left: str,
    right: str,
    *,
    duration_seconds: float | None = None,
) -> RecordingSearchMatch | None:
    """
    Resolve Artist-Title vs Title-Artist by querying MusicBrainz with both orderings.

    Picks the match that best fits duration and filename segments (canonical MB credits).
    """
    left = left.strip()
    right = right.strip()
    if not left or not right:
        return None

    best: RecordingSearchMatch | None = None
    best_rank = float("-inf")
    orderings = ((left, right), (right, left))
    for index, (artist, title) in enumerate(orderings):
        if index > 0:
            time.sleep(1.1)
        hit = search_recording_match(artist, title, duration_seconds=duration_seconds)
        if hit is None:
            continue
        rank = _rank_search_hit(hit, left, right, duration_seconds=duration_seconds)
        if rank > best_rank:
            best = hit
            best_rank = rank
    return best


def _rank_search_hit(
    hit: RecordingSearchMatch,
    left: str,
    right: str,
    *,
    duration_seconds: float | None,
) -> float:
    score = 0.0
    if duration_seconds is not None and hit.length_ms is not None:
        delta = abs(hit.length_ms / 1000 - duration_seconds)
        if delta <= 5:
            score += 100.0
        elif delta <= 15:
            score += 75.0
        elif delta <= 45:
            score += 40.0
        else:
            score -= min(delta, 120.0)

    artist_fold = hit.artist.casefold()
    title_fold = hit.title.casefold()
    left_fold = left.casefold()
    right_fold = right.casefold()

    if _segment_matches(artist_fold, left_fold) and _segment_matches(title_fold, right_fold):
        score += 25.0
    if _segment_matches(artist_fold, right_fold) and _segment_matches(title_fold, left_fold):
        score += 25.0
    return score


def _segment_matches(canonical: str, segment: str) -> bool:
    if not canonical or not segment:
        return False
    return canonical == segment or segment in canonical or canonical in segment


def _search_recordings(query: str, *, limit: int = 5) -> list[dict[str, object]]:
    data = _mb_get(f"{MB_BASE}/recording", {"query": query, "fmt": "json", "limit": limit})
    if data is None:
        logger.warning("musicbrainz_search_failed", query=query)
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
    artist, title, _ = normalize_track_credits(artist, title.strip(), None)
    return RecordingSearchMatch(
        artist=artist,
        title=title,
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
    """
    Fetch genre/subgenre from MusicBrainz.

    Tries recording tags first, then linked releases, then primary artist tags.
    """
    if not recording_id:
        return RecordingGenreInfo(None, None)

    data = _mb_get(
        f"{MB_BASE}/recording/{recording_id}",
        {"inc": "artist-credits+genres+tags+releases", "fmt": "json"},
    )
    if data is None:
        logger.warning("musicbrainz_lookup_failed", recording_id=recording_id)
        return RecordingGenreInfo(None, None, recording_id)

    parsed = _parse_entity_genres(data)
    if parsed.genre:
        return RecordingGenreInfo(
            genre=parsed.genre,
            subgenre=parsed.subgenre,
            musicbrainz_recording_id=recording_id,
        )

    for release_id in _release_ids_from_recording(data, limit=3):
        release_data = _mb_get(
            f"{MB_BASE}/release/{release_id}",
            {"inc": "genres+tags", "fmt": "json"},
        )
        if release_data is None:
            continue
        release_parsed = _parse_entity_genres(release_data)
        if release_parsed.genre:
            return RecordingGenreInfo(
                genre=release_parsed.genre,
                subgenre=release_parsed.subgenre,
                musicbrainz_recording_id=recording_id,
            )

    for artist_id in _artist_ids_from_recording(data, limit=2):
        artist_data = _mb_get(
            f"{MB_BASE}/artist/{artist_id}",
            {"inc": "genres+tags", "fmt": "json"},
        )
        if artist_data is None:
            continue
        artist_parsed = _parse_entity_genres(artist_data)
        if artist_parsed.genre:
            return RecordingGenreInfo(
                genre=artist_parsed.genre,
                subgenre=artist_parsed.subgenre,
                musicbrainz_recording_id=recording_id,
            )

    return RecordingGenreInfo(
        genre=parsed.genre,
        subgenre=parsed.subgenre,
        musicbrainz_recording_id=recording_id,
    )


def _parse_entity_genres(data: dict[str, object]) -> RecordingGenreInfo:
    genres = _sorted_names(data.get("genres"))
    tags = _sorted_names(data.get("tags"))

    genre = title_case_genre(genres[0]) if genres else None
    if genre is None and tags:
        genre = title_case_genre(tags[0])

    subgenre = _pick_subgenre(genre, genres, tags)
    return RecordingGenreInfo(genre=genre, subgenre=subgenre)


def _release_ids_from_recording(data: dict[str, object], *, limit: int) -> list[str]:
    releases = data.get("releases")
    if not isinstance(releases, list):
        return []

    ids: list[str] = []
    for release in releases:
        if not isinstance(release, dict):
            continue
        release_id = release.get("id")
        if isinstance(release_id, str) and release_id and release_id not in ids:
            ids.append(release_id)
        if len(ids) >= limit:
            break
    return ids


def _artist_ids_from_recording(data: dict[str, object], *, limit: int) -> list[str]:
    credits = data.get("artist-credit")
    if not isinstance(credits, list):
        return []

    ids: list[str] = []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        artist = credit.get("artist")
        if not isinstance(artist, dict):
            continue
        artist_id = artist.get("id")
        if isinstance(artist_id, str) and artist_id and artist_id not in ids:
            ids.append(artist_id)
        if len(ids) >= limit:
            break
    return ids


def _throttle_musicbrainz() -> None:
    global _mb_last_request_at
    elapsed = time.monotonic() - _mb_last_request_at
    if elapsed < _MB_MIN_INTERVAL:
        time.sleep(_MB_MIN_INTERVAL - elapsed)
    _mb_last_request_at = time.monotonic()


def _mb_get(url: str, params: dict[str, object]) -> dict[str, object] | None:
    _throttle_musicbrainz()
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("musicbrainz_request_failed", url=url, error=str(exc))
        return None
    except Exception as exc:
        logger.warning("musicbrainz_request_error", url=url, error=str(exc))
        return None

    if not isinstance(data, dict):
        return None
    return data


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
