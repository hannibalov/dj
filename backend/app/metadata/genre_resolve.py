"""Combine embedded file genres with MusicBrainz lookup."""

from pathlib import Path

from app.metadata.genre import format_genre_tag, genre_from_file_tags, parse_embedded_genre
from app.metadata.musicbrainz_lookup import (
    RecordingGenreInfo,
    lookup_recording_genres,
    search_recording_id,
)
from app.metadata.tags import read_tags


def resolve_track_genres(
    *,
    audio_path: Path,
    musicbrainz_recording_id: str | None,
    artist: str | None = None,
    title: str | None = None,
) -> RecordingGenreInfo:
    """
    Resolve genre/subgenre from MusicBrainz (by recording ID or artist/title search)
    with embedded tag fallback.
    """
    embedded = genre_from_file_tags(read_tags(audio_path))

    recording_id = musicbrainz_recording_id
    if not recording_id and artist and title:
        recording_id = search_recording_id(artist, title)

    if recording_id:
        mb = lookup_recording_genres(recording_id)
        genre = mb.genre or embedded[0]
        subgenre = mb.subgenre
        if subgenre is None and embedded[1]:
            subgenre = embedded[1]
        elif subgenre is None and embedded[0] and genre and embedded[0].casefold() != genre.casefold():
            subgenre = embedded[0]
        return RecordingGenreInfo(
            genre=genre,
            subgenre=subgenre,
            musicbrainz_recording_id=recording_id,
        )

    return RecordingGenreInfo(
        genre=embedded[0],
        subgenre=embedded[1],
        musicbrainz_recording_id=None,
    )


def apply_resolved_genres_to_file(
    audio_path: Path,
    *,
    genre: str | None,
    subgenre: str | None,
    artist: str | None,
    title: str | None,
    album: str | None,
) -> None:
    """Write genre (and preserve artist/title/album) to the audio file."""
    from app.metadata.tags import write_tags

    write_tags(
        audio_path,
        artist=artist,
        title=title,
        album=album,
        genre=format_genre_tag(genre, subgenre),
    )
