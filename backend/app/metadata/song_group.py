"""Same-song grouping keys for metadata-based duplicate review."""

from app.models.track import Track


def song_group_key(track: Track) -> str | None:
    """Stable key for grouping tracks that represent the same song."""
    if track.musicbrainz_recording_id:
        return f"mbid:{track.musicbrainz_recording_id}"
    if track.artist and track.title:
        artist = track.artist.strip().casefold()
        title = track.title.strip().casefold()
        mix = (track.mix_version or "").strip().casefold()
        return f"meta:{artist}|{title}|{mix}"
    return None


def song_group_label(track: Track) -> str | None:
    if not track.artist or not track.title:
        return track.title or track.artist
    mix = f" ({track.mix_version})" if track.mix_version else ""
    return f"{track.artist} — {track.title}{mix}"


def track_eligible_for_song_review(track: Track) -> bool:
    """Track has been tagged or manually edited and can join same-song review."""
    from app.models.enums import TrackStatus

    if track.status == TrackStatus.ARCHIVED:
        return False
    if track.tagged_at is None:
        return False
    return song_group_key(track) is not None
