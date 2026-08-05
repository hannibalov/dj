"""Library-wide sanity checks: detect likely-reversed or artist-polluted metadata."""

import re
from collections.abc import Collection

from app.metadata.known_artists import match_known_artist

# A single trailing "(...)" block, e.g. a mix/remix credit like "(Eric Prydz Remix)".
# Deliberately not reused from rename.py's strip_trailing_mix_labels (which special-cases
# junk labels like "Official Video") or normalize.py's strip_junk_parentheticals (which only
# strips a fixed allowlist of non-mix suffixes) — here we want to strip *any* trailing
# parenthetical, since a remix credit legitimately mentioning the artist should not count as
# "artist leaked into title".
_TRAILING_PARENTHETICAL = re.compile(r"\s*\(([^()]*)\)\s*$")

_MIN_ARTIST_LENGTH_FOR_CONTAINMENT = 4


def _strip_trailing_parenthetical(text: str) -> str:
    """Remove one trailing '(...)' block (e.g. a mix/remix credit) before containment checks."""
    stripped = text.strip()
    match = _TRAILING_PARENTHETICAL.search(stripped)
    if match:
        return stripped[: match.start()].strip()
    return stripped


def detect_possible_swap(artist: str, title: str, known_artists: Collection[str]) -> bool:
    """
    True when the title looks like a known library artist but the artist field doesn't.

    Asymmetric signal: "if the song name matches a band name, it's probably reversed."
    """
    return (
        match_known_artist(title, known_artists) is not None
        and match_known_artist(artist, known_artists) is None
    )


def title_contains_artist(artist: str, title: str) -> bool:
    """
    True when the artist name appears inside the title, after stripping a trailing
    mix/remix-credit parenthetical (so "Opus (Eric Prydz Remix)" doesn't falsely flag
    against artist "Eric Prydz" — the remix credit legitimately names the artist).

    Skipped for short artist names (< 4 chars) to avoid constant false positives on
    containment checks (e.g. "Air", "M83").
    """
    stripped_artist = artist.strip()
    if len(stripped_artist) < _MIN_ARTIST_LENGTH_FOR_CONTAINMENT:
        return False

    stripped_title = _strip_trailing_parenthetical(title)
    return stripped_artist.casefold() in stripped_title.casefold()
