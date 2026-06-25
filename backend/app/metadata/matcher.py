"""Combine AcoustID, MusicBrainz, embedded tags, and filename hints into match metadata."""

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from app.metadata.acoustid_lookup import AcoustIdMatch, lookup_by_fingerprint
from app.metadata.artist_title import embedded_tags_swapped
from app.metadata.musicbrainz_lookup import RecordingSearchMatch, search_recording_best
from app.metadata.normalize import names_align, normalize_embedded_tags
from app.metadata.rename import normalize_track_credits
from app.metadata.tags import parse_filename_metadata, read_tags
from app.metadata.types import FileTags


@dataclass(frozen=True)
class MetadataMatch:
    artist: str
    title: str
    album: str | None
    mix_version: str | None
    musicbrainz_recording_id: str | None
    confidence: float
    source: str
    genre: str | None = None
    subgenre: str | None = None


def match_track_metadata(
    path: Path,
    *,
    raw_fingerprint: str | None,
    duration_seconds: float | None,
    acoustid_api_key: str | None,
    confidence_threshold: float,
    reprocess: bool = False,
    filename_hint_path: Path | None = None,
    known_artists: Collection[str] | None = None,
) -> MetadataMatch | None:
    """Return best metadata match or None when nothing usable was found."""
    candidates: list[MetadataMatch] = []

    if acoustid_api_key and raw_fingerprint and duration_seconds:
        acoustid = lookup_by_fingerprint(
            acoustid_api_key,
            raw_fingerprint,
            duration_seconds,
        )
        if acoustid is not None:
            candidates.append(_from_acoustid(acoustid))

    filename_paths: list[Path] = []
    if filename_hint_path is not None and filename_hint_path.is_file():
        filename_paths.append(filename_hint_path)
    if path not in filename_paths:
        filename_paths.append(path)

    segments = _filename_segments(*filename_paths)
    if segments is not None:
        mb = search_recording_best(
            segments[0],
            segments[1],
            duration_seconds=duration_seconds,
        )
        if mb is not None:
            candidates.append(_from_musicbrainz(mb))

    parsed = _best_filename_match(*filename_paths, known_artists=known_artists)
    embedded_raw = read_tags(path)

    if not reprocess:
        embedded = normalize_embedded_tags(
            embedded_raw.artist,
            embedded_raw.title,
            filename=parsed if parsed.artist and parsed.title else None,
        )
        if embedded.artist and embedded.title:
            confidence = 0.62
            if _corroborates_any(candidates, embedded):
                confidence = 0.78
            elif (
                parsed.artist
                and parsed.title
                and (
                    embedded.artist != embedded_raw.artist
                    or embedded.title != embedded_raw.title
                )
            ):
                confidence = 0.72
            candidates.append(
                MetadataMatch(
                    artist=embedded.artist,
                    title=embedded.title,
                    album=embedded_raw.album,
                    mix_version=None,
                    musicbrainz_recording_id=None,
                    confidence=confidence,
                    source="embedded_tags",
                )
            )

    if parsed.artist and parsed.title:
        filename_confidence = 0.52 if reprocess else 0.48
        if not reprocess:
            embedded = normalize_embedded_tags(
                embedded_raw.artist,
                embedded_raw.title,
                filename=parsed,
            )
            if embedded_raw.artist and embedded_raw.title and embedded_tags_swapped(embedded, parsed):
                filename_confidence = 0.68
            elif not embedded_raw.artist and not embedded_raw.title:
                filename_confidence = 0.58
        elif filename_hint_path is not None and filename_hint_path in filename_paths:
            filename_confidence = 0.62
        candidates.append(
            MetadataMatch(
                artist=parsed.artist,
                title=parsed.title,
                album=parsed.album,
                mix_version=None,
                musicbrainz_recording_id=None,
                confidence=filename_confidence,
                source="filename",
            )
        )

    if not candidates:
        return None

    best = max(candidates, key=lambda c: c.confidence)
    return _normalize_match(best)


def _normalize_match(match: MetadataMatch) -> MetadataMatch:
    artist, title, mix = normalize_track_credits(match.artist, match.title, match.mix_version)
    if (
        artist == match.artist
        and title == match.title
        and mix == match.mix_version
    ):
        return match
    return MetadataMatch(
        artist=artist,
        title=title,
        album=match.album,
        mix_version=mix,
        musicbrainz_recording_id=match.musicbrainz_recording_id,
        confidence=match.confidence,
        source=match.source,
        genre=match.genre,
        subgenre=match.subgenre,
    )


def _filename_segments(*paths: Path) -> tuple[str, str] | None:
    """Raw 'left - right' stem segments (order not yet resolved)."""
    best: tuple[str, str] | None = None
    best_score = -1
    for path in paths:
        stem = path.stem
        if " - " not in stem:
            continue
        left, right = stem.split(" - ", 1)
        left, right = left.strip(), right.strip()
        if not left or not right:
            continue
        score = len(left) + len(right)
        if score > best_score:
            best = (left, right)
            best_score = score
    return best


def _best_filename_match(
    *paths: Path,
    known_artists: Collection[str] | None = None,
) -> FileTags:
    """Pick the strongest artist/title parse among one or more file paths."""
    best: FileTags = FileTags(artist=None, title=None, album=None)
    best_score = -1.0
    for path in paths:
        parsed = parse_filename_metadata(path, known_artists=known_artists)
        if not parsed.artist or not parsed.title:
            continue
        score = len(parsed.artist) + len(parsed.title)
        if score > best_score:
            best = parsed
            best_score = score
    return best


def needs_metadata_review(match: MetadataMatch | None, *, threshold: float) -> bool:
    if match is None:
        return True
    return match.confidence < threshold


def _from_acoustid(acoustid: AcoustIdMatch) -> MetadataMatch:
    return MetadataMatch(
        artist=acoustid.artist,
        title=acoustid.title,
        album=acoustid.album,
        mix_version=acoustid.mix_version,
        musicbrainz_recording_id=acoustid.recording_id,
        confidence=acoustid.score,
        source="acoustid",
    )


def _from_musicbrainz(hit: RecordingSearchMatch) -> MetadataMatch:
    return MetadataMatch(
        artist=hit.artist,
        title=hit.title,
        album=None,
        mix_version=None,
        musicbrainz_recording_id=hit.musicbrainz_recording_id,
        confidence=_musicbrainz_confidence(hit),
        source="musicbrainz",
    )


def _musicbrainz_confidence(hit: RecordingSearchMatch) -> float:
    return 0.94


def _corroborates_any(candidates: list[MetadataMatch], tags: FileTags) -> bool:
    if not tags.artist or not tags.title:
        return False
    trusted_sources = frozenset({"acoustid", "musicbrainz"})
    for candidate in candidates:
        if candidate.source not in trusted_sources:
            continue
        if names_align(tags.artist, candidate.artist) and names_align(tags.title, candidate.title):
            return True
        if names_align(tags.artist, candidate.title) and names_align(tags.title, candidate.artist):
            return True
    return False
