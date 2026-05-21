from dataclasses import dataclass


@dataclass(frozen=True)
class FileTags:
    artist: str | None = None
    title: str | None = None
    album: str | None = None
    genre: str | None = None
