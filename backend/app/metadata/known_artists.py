"""Match filename segments against artist names already stored in the library."""

from collections.abc import Collection
from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.metadata.normalize import names_align
from app.models.track import Track

_FUZZY_RATIO_THRESHOLD = 0.86


def load_known_artists(db: Session) -> frozenset[str]:
    """Distinct artist names from confidently tagged tracks in the library."""
    threshold = get_settings().tag_confidence_threshold
    rows = db.execute(
        select(Track.artist)
        .where(
            Track.artist.isnot(None),
            Track.artist != "",
            Track.tagged_at.isnot(None),
            Track.needs_metadata_review.is_(False),
            or_(
                Track.musicbrainz_recording_id.isnot(None),
                Track.tag_confidence >= threshold,
            ),
        )
        .distinct()
    ).scalars()
    return frozenset(artist.strip() for artist in rows if artist and artist.strip())


def match_known_artist(name: str, known_artists: Collection[str]) -> str | None:
    """Return the canonical catalog artist when name matches exactly, aligns, or is a close misspelling."""
    cleaned = name.strip()
    if not cleaned or not known_artists:
        return None

    folded = cleaned.casefold()
    for artist in known_artists:
        if artist.casefold() == folded:
            return artist

    for artist in known_artists:
        if names_align(cleaned, artist):
            return artist

    best: str | None = None
    best_ratio = _FUZZY_RATIO_THRESHOLD
    for artist in known_artists:
        ratio = SequenceMatcher(None, folded, artist.casefold()).ratio()
        if ratio >= best_ratio:
            best_ratio = ratio
            best = artist
    return best
