"""Same-song duplicate groups — metadata / MusicBrainz, not fingerprint identity."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.fingerprint.version_priority import preferred_track_ids
from app.metadata.song_group import (
    canonical_group_key,
    cluster_song_groups,
    group_match_type,
    song_group_label,
)
from app.models.enums import TrackStatus
from app.models.track import Track
from app.schemas.song_duplicate import SongDuplicateGroupMember, SongDuplicateGroupResponse
from app.services.duplicate_service import DuplicateService
from app.utils.audio_format import get_format_info


class SongDuplicateService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_groups(self) -> list[SongDuplicateGroupResponse]:
        tracks = self._load_tracks()
        result: list[SongDuplicateGroupResponse] = []

        for members in cluster_song_groups(tracks):
            if not self._is_cross_fingerprint_group(members):
                continue

            group_key = canonical_group_key(members)
            label_track = next((t for t in members if t.artist and t.title), members[0])
            label = song_group_label(label_track) or group_key
            member_responses = [self._member_response(track) for track in members]
            mbids = {t.musicbrainz_recording_id for t in members if t.musicbrainz_recording_id}

            result.append(
                SongDuplicateGroupResponse(
                    group_key=group_key,
                    match_type=group_match_type(members),
                    label=label,
                    musicbrainz_recording_id=next(iter(mbids)) if len(mbids) == 1 else None,
                    suggested_keep_track_id=self._suggested_keep(members),
                    members=member_responses,
                )
            )

        result.sort(key=lambda group: group.label.casefold())
        return result

    def members_for_group_key(self, group_key: str) -> list[Track]:
        for members in cluster_song_groups(self._load_tracks()):
            if canonical_group_key(members) != group_key:
                continue
            if len(members) < 2:
                return []
            if not self._is_cross_fingerprint_group(members):
                return []
            return members
        return []

    def _load_tracks(self) -> list[Track]:
        return list(
            self._db.execute(
                select(Track)
                .options(joinedload(Track.fingerprint))
                .where(Track.status != TrackStatus.ARCHIVED)
                .order_by(Track.id)
            )
            .unique()
            .scalars()
            .all()
        )

    @staticmethod
    def _is_cross_fingerprint_group(members: list[Track]) -> bool:
        """Same-song review applies when audio fingerprints differ."""
        hashes: set[str] = set()
        with_fp = 0
        for track in members:
            fp = track.fingerprint
            if fp is None:
                continue
            with_fp += 1
            hashes.add(fp.fingerprint_hash)
        if with_fp == 0:
            return True
        if with_fp < len(members):
            return True
        return len(hashes) >= 2

    def _member_response(self, track: Track) -> SongDuplicateGroupMember:
        fp = track.fingerprint
        path = DuplicateService._member_path(track)
        ext = path.suffix.lower() if path else ""
        bitrate = None
        if path and path.is_file():
            bitrate = get_format_info(path).bitrate_kbps

        return SongDuplicateGroupMember(
            track_id=track.id,
            status=track.status,
            source_path=track.source_path,
            final_path=track.final_path,
            fingerprint_hash=fp.fingerprint_hash if fp else None,
            duration_seconds=fp.duration_seconds if fp else None,
            format_extension=ext or None,
            bitrate_kbps=bitrate,
            artist=track.artist,
            title=track.title,
            integrated_lufs=track.integrated_lufs,
            energy=track.energy,
            bpm=track.bpm,
            camelot=track.camelot,
        )

    @staticmethod
    def _suggested_keep(members: list[Track]) -> int | None:
        preferred = preferred_track_ids(members)
        if not preferred:
            return members[0].id if members else None
        if len(preferred) == 1:
            return next(iter(preferred))
        return min(preferred)
