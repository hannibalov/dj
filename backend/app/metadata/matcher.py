"""Combine AcoustID, embedded tags, and filename hints into match metadata."""

from dataclasses import dataclass
from pathlib import Path

from app.metadata.acoustid_lookup import AcoustIdMatch, lookup_by_fingerprint
from app.metadata.artist_title import embedded_tags_swapped
from app.metadata.musicbrainz_lookup import RecordingSearchMatch, search_recording_match
from app.metadata.normalize import normalize_embedded_tags
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

    parsed = _best_filename_match(*filename_paths)
    embedded_raw = read_tags(path)

    if not reprocess:
        embedded = normalize_embedded_tags(
            embedded_raw.artist,
            embedded_raw.title,
            filename=parsed if parsed.artist and parsed.title else None,
        )
        if embedded.artist and embedded.title:
            confidence = 0.75
            if (
                parsed.artist
                and parsed.title
                and (
                    embedded.artist != embedded_raw.artist
                    or embedded.title != embedded_raw.title
                )
            ):
                confidence = 0.8
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
        filename_confidence = 0.7 if reprocess else 0.55
        if not reprocess:
            embedded = normalize_embedded_tags(
                embedded_raw.artist,
                embedded_raw.title,
                filename=parsed,
            )
            if embedded_raw.artist and embedded_raw.title and embedded_tags_swapped(embedded, parsed):
                filename_confidence = 0.82
            elif not embedded_raw.artist and not embedded_raw.title:
                filename_confidence = 0.65
        elif filename_hint_path is not None and filename_hint_path in filename_paths:
            filename_confidence = 0.78
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
    if _should_search_musicbrainz(best, threshold=confidence_threshold, parsed=parsed):
        mb_match = _match_from_musicbrainz_search(
            parsed,
            duration_seconds=duration_seconds,
        )
        if mb_match is not None:
            candidates.append(mb_match)

    return max(candidates, key=lambda c: c.confidence)


def _best_filename_match(*paths: Path) -> FileTags:
    """Pick the strongest artist/title parse among one or more file paths."""
    best: FileTags = FileTags(artist=None, title=None, album=None)
    best_score = -1.0
    for path in paths:
        parsed = parse_filename_metadata(path)
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


def _should_search_musicbrainz(
    best: MetadataMatch,
    *,
    threshold: float,
    parsed: FileTags,
) -> bool:
    """Use MusicBrainz text search when filename hints exist but confidence is low."""
    if not parsed.artist or not parsed.title:
        return False
    if best.confidence >= threshold:
        return False
    return True


def _match_from_musicbrainz_search(
    parsed: FileTags,
    *,
    duration_seconds: float | None,
) -> MetadataMatch | None:
    assert parsed.artist and parsed.title
    hit = search_recording_match(
        parsed.artist,
        parsed.title,
        duration_seconds=duration_seconds,
    )
    if hit is None:
        return None
    return MetadataMatch(
        artist=hit.artist,
        title=hit.title,
        album=None,
        mix_version=None,
        musicbrainz_recording_id=hit.musicbrainz_recording_id,
        confidence=_musicbrainz_search_confidence(hit, duration_seconds=duration_seconds),
        source="musicbrainz_search",
    )


def _musicbrainz_search_confidence(
    hit: RecordingSearchMatch,
    *,
    duration_seconds: float | None,
) -> float:
    confidence = 0.88
    if duration_seconds is None or hit.length_ms is None:
        return confidence

    delta_seconds = abs(hit.length_ms / 1000 - duration_seconds)
    if delta_seconds <= 5:
        return 0.93
    if delta_seconds <= 15:
        return 0.9
    if delta_seconds > 45:
        return 0.78
    return confidence
