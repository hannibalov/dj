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


def extract_mix_from_title(title: str) -> tuple[str, str | None]:
    """Split 'Title (Club Mix)' into title and mix label."""
    match = _TRAILING_MIX.match(title.strip())
    if not match:
        return title.strip(), None
    mix_label = match.group(2).strip()
    if mix_label.casefold() in _JUNK_MIX_LABELS:
        return title.strip(), None
    return match.group(1).strip(), mix_label


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
    base_title, extracted_mix = extract_mix_from_title(title)
    mix_label = mix or extracted_mix or "Original Mix"
    safe_artist = sanitize_filename_part(artist)
    safe_title = sanitize_filename_part(base_title)
    safe_mix = sanitize_filename_part(mix_label)

    pattern = template or DEFAULT_NAMING_TEMPLATE
    rendered = pattern.format(
        artist=safe_artist,
        title=safe_title,
        mix=safe_mix,
        ext=ext,
    )
    return Path(rendered).name
