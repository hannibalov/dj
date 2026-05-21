"""Combine embedded file genres with MusicBrainz lookup."""

from pathlib import Path

from app.metadata.genre import genre_from_file_tags, parse_embedded_genre
from app.metadata.musicbrainz_lookup import RecordingGenreInfo, lookup_recording_genres
from app.metadata.tags import read_tags


def resolve_track_genres(
    *,
    audio_path: Path,
    musicbrainz_recording_id: str | None,
) -> RecordingGenreInfo:
    embedded = genre_from_file_tags(read_tags(audio_path))

    if musicbrainz_recording_id:
        mb = lookup_recording_genres(musicbrainz_recording_id)
        genre = mb.genre or embedded[0]
        subgenre = mb.subgenre
        if subgenre is None and embedded[1]:
            subgenre = embedded[1]
        elif subgenre is None and embedded[0] and genre and embedded[0].casefold() != genre.casefold():
            subgenre = embedded[0]
        return RecordingGenreInfo(genre=genre, subgenre=subgenre)

    return RecordingGenreInfo(genre=embedded[0], subgenre=embedded[1])
