"""DJ library filename builder and sanitizer."""

import re
from pathlib import Path

DEFAULT_NAMING_TEMPLATE = "{title} - {artist} ({mix}){ext}"

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_TRAILING_MIX = re.compile(r"^(.+?)\s+\(([^)]+)\)\s*$")
_JUNK_MIX_LABELS = frozenset(
    label.casefold()
    for label in (
        "Official Music Video",
        "Official Video",
        "Music Video",
        "Lyric Video",
        "Lyrics",
        "HD",
        "4K",
        "Visualizer",
        "Audio",
    )
)


def sanitize_filename_part(text: str) -> str:
    """Remove filesystem-unsafe characters and trim."""
    cleaned = _UNSAFE_CHARS.sub("", text).strip(" .")
    return cleaned or "Unknown"


def strip_trailing_mix_labels(text: str) -> tuple[str, str | None]:
    """Remove trailing (Mix Label) suffixes, including repeated ones."""
    text = text.strip()
    extracted: str | None = None
    while True:
        match = _TRAILING_MIX.match(text)
        if not match:
            break
        mix_label = match.group(2).strip()
        if mix_label.casefold() in _JUNK_MIX_LABELS:
            break
        extracted = mix_label
        text = match.group(1).strip()
    return text, extracted


def extract_mix_from_title(title: str) -> tuple[str, str | None]:
    """Split 'Title (Club Mix)' into title and mix label."""
    return strip_trailing_mix_labels(title.strip())


def normalize_track_credits(
    artist: str,
    title: str,
    mix: str | None = None,
) -> tuple[str, str, str | None]:
    """Strip mix/version parentheticals from artist and title; keep mix in its own field."""
    clean_artist, artist_mix = strip_trailing_mix_labels(artist)
    clean_title, title_mix = strip_trailing_mix_labels(title)
    resolved_mix = mix or title_mix or artist_mix
    return clean_artist, clean_title, resolved_mix


def build_library_filename(
    *,
    artist: str,
    title: str,
    mix: str | None = None,
    extension: str,
    template: str | None = None,
) -> str:
    """
    Build a library filename per spec: Title - Artist (Mix).ext

    Uses {title}, {artist}, {mix}, {ext} placeholders in template.
    """
    ext = extension if extension.startswith(".") else f".{extension}"
    clean_artist, clean_title, resolved_mix = normalize_track_credits(artist, title, mix)
    mix_label = resolved_mix or "Original Mix"
    safe_artist = sanitize_filename_part(clean_artist)
    safe_title = sanitize_filename_part(clean_title)
    safe_mix = sanitize_filename_part(mix_label)

    pattern = template or DEFAULT_NAMING_TEMPLATE
    rendered = pattern.format(
        artist=safe_artist,
        title=safe_title,
        mix=safe_mix,
        ext=ext,
    )
    return Path(rendered).name
