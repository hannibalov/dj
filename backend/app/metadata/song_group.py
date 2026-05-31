"""Same-song grouping keys for metadata-based duplicate review."""

from collections import defaultdict

from app.models.enums import TrackStatus
from app.models.track import Track


def song_group_keys(track: Track) -> list[str]:
    """Keys used to link tracks that may represent the same song."""
    keys: list[str] = []
    if track.artist and track.title:
        artist = track.artist.strip().casefold()
        title = track.title.strip().casefold()
        mix = (track.mix_version or "").strip().casefold()
        base = f"meta:{artist}|{title}"
        keys.append(f"{base}|{mix}")
        # Link tracks that differ only by missing mix label (common after manual edits).
        keys.append(f"{base}|*")
    if track.musicbrainz_recording_id:
        keys.append(f"mbid:{track.musicbrainz_recording_id}")
    return keys


def song_group_label(track: Track) -> str | None:
    if not track.artist or not track.title:
        return track.title or track.artist
    mix = f" ({track.mix_version})" if track.mix_version else ""
    return f"{track.artist} — {track.title}{mix}"


def track_eligible_for_song_review(track: Track) -> bool:
    """Track has library metadata and can join same-song duplicate review."""
    if track.status == TrackStatus.ARCHIVED:
        return False
    if track.status not in (TrackStatus.READY, TrackStatus.REVIEW, TrackStatus.DUPLICATE):
        return False
    if not track.artist or not track.title:
        return False
    return bool(song_group_keys(track))


def cluster_song_groups(tracks: list[Track]) -> list[list[Track]]:
    """Union tracks that share any song-group key."""
    eligible = [track for track in tracks if track_eligible_for_song_review(track)]
    if not eligible:
        return []

    parent = {track.id: track.id for track in eligible}

    def find(track_id: int) -> int:
        while parent[track_id] != track_id:
            parent[track_id] = parent[parent[track_id]]
            track_id = parent[track_id]
        return track_id

    def union(left_id: int, right_id: int) -> None:
        root_left = find(left_id)
        root_right = find(right_id)
        if root_left != root_right:
            parent[root_right] = root_left

    key_members: dict[str, list[int]] = defaultdict(list)
    for track in eligible:
        for key in song_group_keys(track):
            key_members[key].append(track.id)

    for track_ids in key_members.values():
        anchor = track_ids[0]
        for track_id in track_ids[1:]:
            union(anchor, track_id)

    clusters: dict[int, list[Track]] = defaultdict(list)
    track_by_id = {track.id: track for track in eligible}
    for track in eligible:
        clusters[find(track.id)].append(track)

    return [members for members in clusters.values() if len(members) >= 2]


def canonical_group_key(members: list[Track]) -> str:
    """Stable key for API resolve, derived from cluster members."""
    for track in sorted(members, key=lambda item: item.id):
        for key in song_group_keys(track):
            if key.startswith("meta:") and not key.endswith("|*"):
                return key
    for track in sorted(members, key=lambda item: item.id):
        for key in song_group_keys(track):
            if key.startswith("meta:"):
                return key
    for track in sorted(members, key=lambda item: item.id):
        if track.musicbrainz_recording_id:
            return f"mbid:{track.musicbrainz_recording_id}"
    return f"cluster:{min(track.id for track in members)}"


def group_match_type(members: list[Track]) -> str:
    mbids = {track.musicbrainz_recording_id for track in members if track.musicbrainz_recording_id}
    if len(mbids) == 1:
        return "musicbrainz"
    return "metadata"
