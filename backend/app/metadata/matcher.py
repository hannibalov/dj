"""Combine AcoustID, embedded tags, and filename hints into match metadata."""

from dataclasses import dataclass
from pathlib import Path

from app.metadata.acoustid_lookup import AcoustIdMatch, lookup_by_fingerprint
from app.metadata.artist_title import embedded_tags_swapped
from app.metadata.normalize import normalize_embedded_tags
from app.metadata.tags import parse_filename_metadata, read_tags


@dataclass(frozen=True)
class MetadataMatch:
    artist: str
    title: str
    album: str | None
    mix_version: str | None
    musicbrainz_recording_id: str | None
    confidence: float
    source: str


def match_track_metadata(
    path: Path,
    *,
    raw_fingerprint: str | None,
    duration_seconds: float | None,
    acoustid_api_key: str | None,
    confidence_threshold: float,
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

    parsed = parse_filename_metadata(path)
    embedded_raw = read_tags(path)
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
            and (embedded.artist != embedded_raw.artist or embedded.title != embedded_raw.title)
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
        filename_confidence = 0.55
        if embedded_raw.artist and embedded_raw.title and embedded_tags_swapped(embedded, parsed):
            filename_confidence = 0.82
        elif not embedded_raw.artist and not embedded_raw.title:
            filename_confidence = 0.65
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

    return max(candidates, key=lambda c: c.confidence)


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
