from dataclasses import dataclass


@dataclass(frozen=True)
class FileTags:
    artist: str | None
    title: str | None
    album: str | None
