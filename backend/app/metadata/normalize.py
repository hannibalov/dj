"""Normalize messy embedded tags (e.g. YouTube channel as artist)."""

import re

from app.metadata.types import FileTags

_JUNK_PAREN_SUFFIX = re.compile(
    r"\s*\("
    r"(?:Official Music Video|Official Video|Music Video|Lyric Video|Lyrics|HD|4K|Visualizer|Audio)"
    r"\)\s*$",
    re.IGNORECASE,
)
_CHANNEL_ARTIST = re.compile(
    r"(?:\bTV\b|\bVEVO\b|Official\s+Channel|\bTopic\s*$)",
    re.IGNORECASE,
)


def is_channel_style_artist(artist: str) -> bool:
    """True when artist tag looks like a label/channel, not a performing artist."""
    return bool(_CHANNEL_ARTIST.search(artist.strip()))


def strip_junk_parentheticals(text: str) -> str:
    """Remove trailing (Official Music Video) and similar non-mix suffixes."""
    cleaned = text.strip()
    while True:
        match = _JUNK_PAREN_SUFFIX.search(cleaned)
        if not match:
            break
        cleaned = cleaned[: match.start()].strip()
    return cleaned


def parse_artist_title_from_compound(title: str) -> tuple[str | None, str]:
    """
    Parse 'Performer - Song Name' embedded in the title field.

    Returns (artist, song) or (None, title) when not compound.
    """
    cleaned = strip_junk_parentheticals(title)
    if " - " not in cleaned:
        return None, cleaned

    artist, song = cleaned.split(" - ", 1)
    artist, song = artist.strip(), strip_junk_parentheticals(song.strip())
    if not artist or not song:
        return None, cleaned
    return artist, song


def _names_align(a: str, b: str) -> bool:
    return a.strip().casefold() == b.strip().casefold()


def normalize_embedded_tags(
    artist: str | None,
    title: str | None,
    *,
    filename: FileTags | None = None,
) -> FileTags:
    """
    Prefer performer parsed from compound title over channel-style artist tags.

    When the watch filename is a clean 'Artist - Title', it reinforces the parse.
    """
    if not artist and not title:
        return FileTags(artist=None, title=None, album=None)

    tag_artist = (artist or "").strip()
    tag_title = (title or "").strip()
    if not tag_title:
        return FileTags(artist=tag_artist or None, title=None, album=None)

    title_artist, title_song = parse_artist_title_from_compound(tag_title)
    if not title_artist:
        return FileTags(
            artist=tag_artist or None,
            title=strip_junk_parentheticals(tag_title),
            album=None,
        )

    use_title_artist = is_channel_style_artist(tag_artist)
    if (
        not use_title_artist
        and tag_artist
        and not _names_align(tag_artist, title_artist)
        and tag_title.casefold().startswith(title_artist.casefold())
    ):
        use_title_artist = True

    if (
        not use_title_artist
        and filename
        and filename.artist
        and filename.title
        and _names_align(filename.artist, title_artist)
        and _names_align(filename.title, title_song)
    ):
        use_title_artist = True

    if use_title_artist:
        return FileTags(artist=title_artist, title=title_song, album=None)

    return FileTags(
        artist=tag_artist or None,
        title=strip_junk_parentheticals(tag_title),
        album=None,
    )
