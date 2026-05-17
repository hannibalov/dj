from pathlib import Path
from typing import Protocol


class _HasSuffix(Protocol):
    @property
    def suffix(self) -> str: ...


AUDIO_EXTENSIONS = frozenset({".flac", ".mp3", ".wav", ".aiff", ".aif", ".m4a", ".ogg"})


def is_audio_file(path: Path | _HasSuffix) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS
