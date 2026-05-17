"""Map musical key + scale to Camelot notation (Mixed In Key wheel)."""

_MINOR: dict[str, str] = {
    "G#": "1A",
    "Ab": "1A",
    "D#": "2A",
    "Eb": "2A",
    "A#": "3A",
    "Bb": "3A",
    "F": "4A",
    "C": "5A",
    "G": "6A",
    "D": "7A",
    "A": "8A",
    "E": "9A",
    "B": "10A",
    "F#": "11A",
    "Gb": "11A",
    "C#": "12A",
    "Db": "12A",
}

_MAJOR: dict[str, str] = {
    "B": "1B",
    "F#": "2B",
    "Gb": "2B",
    "Db": "3B",
    "C#": "3B",
    "Ab": "4B",
    "G#": "4B",
    "Eb": "5B",
    "D#": "5B",
    "Bb": "6B",
    "A#": "6B",
    "F": "7B",
    "C": "8B",
    "G": "9B",
    "D": "10B",
    "A": "11B",
    "E": "12B",
}


def to_camelot(key: str, scale: str) -> str | None:
    normalized_scale = scale.lower()
    if normalized_scale == "minor":
        return _MINOR.get(key)
    if normalized_scale == "major":
        return _MAJOR.get(key)
    return None
