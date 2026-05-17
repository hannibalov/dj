"""Resolve Artist - Title vs Title - Artist from filename segments."""

import re

from app.metadata.types import FileTags

_TITLE_MARKERS = (
    " feat.",
    " feat ",
    " ft.",
    " ft ",
    " vs ",
    " vs. ",
)
_FEATURE_IN_PARENS = re.compile(
    r"\s*\((?:feat\.?|ft\.?)[^)]+\)",
    re.IGNORECASE,
)


def _matches(a: str, b: str) -> bool:
    return a.strip().casefold() == b.strip().casefold()


def _score_artist_title_pair(artist: str, title: str) -> int:
    """Higher score means (artist, title) order is more plausible."""
    score = 0
    artist_lower = artist.casefold()
    title_lower = title.casefold()

    if artist_lower.startswith("the "):
        score += 3
    if title_lower.startswith("the "):
        score -= 2

    if any(marker in title_lower for marker in _TITLE_MARKERS):
        score += 2
    if any(marker in artist_lower for marker in _TITLE_MARKERS):
        score -= 3

    if _FEATURE_IN_PARENS.search(title):
        score += 2

    if "(" in title and ")" in title and "mix" in title_lower:
        score += 1

    artist_words = len(artist.split())
    title_words = len(title.split())
    if artist_words >= 2 and title_words > artist_words:
        score += 3
    if title_words >= 2 and artist_words > title_words:
        score -= 3

    return score


def resolve_artist_title(
    left: str,
    right: str,
    embedded: FileTags | None = None,
) -> tuple[str, str]:
    """
    Decide which side is artist vs title.

    Uses embedded tags when present, then structural heuristics.
    For ambiguous single-token pairs with no tags, assumes common download
    order Title - Artist (e.g. Wonderwall - Oasis).
    """
    left, right = left.strip(), right.strip()

    if embedded:
        if embedded.artist:
            if _matches(left, embedded.artist):
                return left, right
            if _matches(right, embedded.artist):
                return right, left
        if embedded.title:
            if _matches(left, embedded.title):
                return right, left
            if _matches(right, embedded.title):
                return left, right

    artist_title = (left, right)
    title_artist = (right, left)
    score_forward = _score_artist_title_pair(*artist_title)
    score_swap = _score_artist_title_pair(*title_artist)

    if score_swap > score_forward:
        return title_artist
    if score_forward > score_swap:
        return artist_title

    if len(left.split()) == 1 and len(right.split()) == 1:
        return title_artist

    return artist_title


def embedded_tags_swapped(embedded: FileTags, resolved: FileTags) -> bool:
    if not embedded.artist or not embedded.title:
        return False
    if not resolved.artist or not resolved.title:
        return False
    return _matches(embedded.artist, resolved.title) and _matches(embedded.title, resolved.artist)
