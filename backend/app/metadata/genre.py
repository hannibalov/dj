"""Genre / subgenre parsing from embedded tags and MusicBrainz."""

import re

from app.metadata.types import FileTags

_GENRE_SPLIT = re.compile(r"\s*[;/|]\s*")


def parse_embedded_genre(raw: str | None) -> tuple[str | None, str | None]:
    """Split compound genre tags like 'Electronic; Techno' into genre + subgenre."""
    if not raw or not raw.strip():
        return None, None
    parts = [p.strip() for p in _GENRE_SPLIT.split(raw.strip()) if p.strip()]
    if not parts:
        return None, None
    if len(parts) == 1:
        return title_case_genre(parts[0]), None
    return title_case_genre(parts[0]), title_case_genre(parts[1])


def title_case_genre(name: str) -> str:
    """Normalize 'techno' / 'DRUM AND BASS' for display."""
    cleaned = " ".join(name.split())
    if not cleaned:
        return cleaned
    if cleaned.isupper() and len(cleaned) > 3:
        return cleaned.title()
    return cleaned[0].upper() + cleaned[1:] if len(cleaned) == 1 else cleaned.title()


def genre_from_file_tags(tags: FileTags) -> tuple[str | None, str | None]:
    return parse_embedded_genre(tags.genre)


def format_genre_tag(genre: str | None, subgenre: str | None) -> str | None:
    if genre and subgenre:
        return f"{genre}; {subgenre}"
    return genre
