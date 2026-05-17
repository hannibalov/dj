"""Read and write audio tags via mutagen."""

from pathlib import Path

from mutagen import File as MutagenFile  # type: ignore[attr-defined]
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

from app.metadata.artist_title import resolve_artist_title
from app.metadata.types import FileTags


def read_tags(path: Path) -> FileTags:
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        return FileTags(artist=None, title=None, album=None)

    if audio is None:
        return FileTags(artist=None, title=None, album=None)

    artist = _first(audio.get("artist"))
    title = _first(audio.get("title"))
    album = _first(audio.get("album"))
    return FileTags(artist=artist, title=title, album=album)


def write_tags(
    path: Path,
    *,
    artist: str,
    title: str,
    album: str | None = None,
) -> None:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        _write_mp3(path, artist=artist, title=title, album=album)
    elif suffix == ".flac":
        _write_flac(path, artist=artist, title=title, album=album)
    else:
        _write_easy(path, artist=artist, title=title, album=album)


def parse_filename_metadata(path: Path) -> FileTags:
    """Parse 'Artist - Title' or 'Title - Artist' from basename using tags + heuristics."""
    stem = path.stem
    if " - " not in stem:
        return FileTags(artist=None, title=None, album=None)

    left, right = stem.split(" - ", 1)
    left, right = left.strip(), right.strip()
    if not left or not right:
        return FileTags(artist=None, title=None, album=None)

    embedded = read_tags(path)
    artist, title = resolve_artist_title(left, right, embedded)
    return FileTags(artist=artist, title=title, album=None)


def _write_mp3(path: Path, *, artist: str, title: str, album: str | None) -> None:
    try:
        audio = MP3(path, ID3=EasyID3)
    except Exception:
        audio = MP3(path)
        audio.add_tags()  # type: ignore[no-untyped-call]
        audio = MP3(path, ID3=EasyID3)

    audio["artist"] = artist
    audio["title"] = title
    if album:
        audio["album"] = album
    audio.save()


def _write_flac(path: Path, *, artist: str, title: str, album: str | None) -> None:
    audio = FLAC(path)
    audio["artist"] = artist
    audio["title"] = title
    if album:
        audio["album"] = album
    audio.save()


def _write_easy(path: Path, *, artist: str, title: str, album: str | None) -> None:
    audio = MutagenFile(path, easy=True)
    if audio is None:
        raise ValueError(f"Unsupported audio format: {path.suffix}")
    audio["artist"] = artist
    audio["title"] = title
    if album:
        audio["album"] = album
    audio.save()


def _first(values: object) -> str | None:
    if not values:
        return None
    if isinstance(values, list):
        return str(values[0]) if values else None
    return str(values)
