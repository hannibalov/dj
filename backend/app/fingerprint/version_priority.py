"""Preferred-version selection for duplicate groups."""

from collections import defaultdict
from pathlib import Path

from app.models.track import Track
from app.utils.audio_format import format_priority, get_format_info


def preferred_track_ids(tracks: list[Track]) -> set[int]:
    """
    Pick the best track per format family.

    Different families (e.g. lossless vs mp3) can each have a preferred copy,
    matching the spec rule to keep FLAC + MP3 variants by default.
    """
    by_family: dict[str, list[Track]] = defaultdict(list)
    for track in tracks:
        path = _track_audio_path(track)
        if path is None:
            continue
        info = get_format_info(path)
        by_family[info.family].append(track)

    preferred: set[int] = set()
    for family_tracks in by_family.values():
        best = min(family_tracks, key=_track_priority_key)
        preferred.add(best.id)
    return preferred


def _track_priority_key(track: Track) -> tuple[int, int]:
    path = _track_audio_path(track)
    if path is None:
        return (99, 0)
    return format_priority(get_format_info(path))


def _track_audio_path(track: Track) -> Path | None:
    if track.processing_path:
        path = Path(track.processing_path)
        if path.is_file():
            return path
    if track.final_path:
        path = Path(track.final_path)
        if path.is_file():
            return path
    return None
