"""Read and write audio tags via mutagen."""

from pathlib import Path
from typing import Callable

from mutagen import File as MutagenFile  # type: ignore[attr-defined]
from mutagen.aiff import AIFF
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError, TALB, TCON, TIT2, TPE1
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

from app.metadata.rename import normalize_track_credits
from app.metadata.artist_title import resolve_artist_title
from app.metadata.types import FileTags

_ID3_CHUNK_SUFFIXES = frozenset({".wav", ".aiff", ".aif"})


def read_tags(path: Path) -> FileTags:
    suffix = path.suffix.lower()
    if suffix in _ID3_CHUNK_SUFFIXES:
        return _read_id3_chunk_tags(path)

    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        return FileTags()

    if audio is None:
        return FileTags()

    return FileTags(
        artist=_first(audio.get("artist")),
        title=_first(audio.get("title")),
        album=_first(audio.get("album")),
        genre=_first(audio.get("genre")),
    )


def write_tags(
    path: Path,
    *,
    artist: str,
    title: str,
    album: str | None = None,
    genre: str | None = None,
) -> None:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        _write_mp3(path, artist=artist, title=title, album=album, genre=genre)
    elif suffix == ".flac":
        _write_flac(path, artist=artist, title=title, album=album, genre=genre)
    elif suffix == ".wav":
        _write_id3_chunk(path, WAVE, artist=artist, title=title, album=album, genre=genre)
    elif suffix in (".aiff", ".aif"):
        _write_id3_chunk(path, AIFF, artist=artist, title=title, album=album, genre=genre)
    else:
        _write_easy(path, artist=artist, title=title, album=album, genre=genre)


def parse_filename_metadata(path: Path) -> FileTags:
    """Parse 'Artist - Title' or 'Title - Artist' from basename using tags + heuristics."""
    stem = path.stem
    if " - " not in stem:
        return FileTags()

    left, right = stem.split(" - ", 1)
    left, right = left.strip(), right.strip()
    if not left or not right:
        return FileTags()

    embedded = read_tags(path)
    artist, title = resolve_artist_title(left, right, embedded)
    artist, title, _ = normalize_track_credits(artist, title, None)
    return FileTags(artist=artist, title=title, album=embedded.album, genre=embedded.genre)


def _write_mp3(path: Path, *, artist: str, title: str, album: str | None, genre: str | None) -> None:
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
    if genre:
        audio["genre"] = genre
    audio.save()


def _write_flac(path: Path, *, artist: str, title: str, album: str | None, genre: str | None) -> None:
    audio = FLAC(path)
    audio["artist"] = artist
    audio["title"] = title
    if album:
        audio["album"] = album
    if genre:
        audio["genre"] = genre
    audio.save()


def _write_easy(path: Path, *, artist: str, title: str, album: str | None, genre: str | None) -> None:
    audio = MutagenFile(path, easy=True)
    if audio is None:
        raise ValueError(f"Unsupported audio format: {path.suffix}")
    audio["artist"] = artist
    audio["title"] = title
    if album:
        audio["album"] = album
    if genre:
        audio["genre"] = genre
    audio.save()


def _read_id3_chunk_tags(path: Path) -> FileTags:
    suffix = path.suffix.lower()
    loader: Callable[[Path], WAVE | AIFF]
    if suffix == ".wav":
        loader = WAVE
    else:
        loader = AIFF
    try:
        audio = loader(path)
    except Exception:
        return FileTags()
    try:
        tags = audio.tags
    except ID3NoHeaderError:
        return FileTags()
    if tags is None:
        return FileTags()
    return FileTags(
        artist=_id3_text(tags.get("TPE1")),
        title=_id3_text(tags.get("TIT2")),
        album=_id3_text(tags.get("TALB")),
        genre=_id3_text(tags.get("TCON")),
    )


def _write_id3_chunk(
    path: Path,
    loader: Callable[[Path], WAVE | AIFF],
    *,
    artist: str,
    title: str,
    album: str | None,
    genre: str | None,
) -> None:
    audio = loader(path)
    try:
        if audio.tags is None:
            raise ID3NoHeaderError()
    except ID3NoHeaderError:
        audio.add_tags()
    _apply_id3_frames(audio.tags, artist=artist, title=title, album=album, genre=genre)
    audio.save()


def _apply_id3_frames(
    tags: object,
    *,
    artist: str,
    title: str,
    album: str | None,
    genre: str | None,
) -> None:
    tags.setall("TPE1", [TPE1(encoding=3, text=artist)])  # type: ignore[union-attr]
    tags.setall("TIT2", [TIT2(encoding=3, text=title)])  # type: ignore[union-attr]
    if album:
        tags.setall("TALB", [TALB(encoding=3, text=album)])  # type: ignore[union-attr]
    else:
        tags.delall("TALB")  # type: ignore[union-attr]
    if genre:
        tags.setall("TCON", [TCON(encoding=3, text=genre)])  # type: ignore[union-attr]
    else:
        tags.delall("TCON")  # type: ignore[union-attr]


def _id3_text(frame: object) -> str | None:
    if frame is None:
        return None
    text = getattr(frame, "text", None)
    if not text:
        return None
    return str(text[0])


def _first(values: object) -> str | None:
    if not values:
        return None
    if isinstance(values, list):
        return str(values[0]) if values else None
    return str(values)
