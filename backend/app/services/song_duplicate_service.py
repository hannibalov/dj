"""Same-song duplicate groups — metadata / MusicBrainz, not fingerprint identity."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.fingerprint.version_priority import preferred_track_ids
from app.metadata.song_group import song_group_key, song_group_label, track_eligible_for_song_review
from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.track import Track
from app.schemas.song_duplicate import SongDuplicateGroupMember, SongDuplicateGroupResponse
from app.services.duplicate_service import DuplicateService
from app.utils.audio_format import get_format_info


class SongDuplicateService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_groups(self) -> list[SongDuplicateGroupResponse]:
        tracks = (
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

        by_key: dict[str, list[Track]] = {}
        for track in tracks:
            if not track_eligible_for_song_review(track):
                continue
            key = song_group_key(track)
            if key is None:
                continue
            by_key.setdefault(key, []).append(track)

        result: list[SongDuplicateGroupResponse] = []
        for key, members in sorted(by_key.items(), key=lambda item: item[0]):
            if len(members) < 2:
                continue
            if not self._is_cross_fingerprint_group(members):
                continue

            match_type = "musicbrainz" if key.startswith("mbid:") else "metadata"
            label_track = next((t for t in members if t.artist and t.title), members[0])
            label = song_group_label(label_track) or key
            member_responses = [self._member_response(track) for track in members]
            suggested = self._suggested_keep(members)

            result.append(
                SongDuplicateGroupResponse(
                    group_key=key,
                    match_type=match_type,
                    label=label,
                    musicbrainz_recording_id=label_track.musicbrainz_recording_id,
                    suggested_keep_track_id=suggested,
                    members=member_responses,
                )
            )
        return result

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

    def members_for_group_key(self, group_key: str) -> list[Track]:
        tracks = (
            self._db.execute(
                select(Track)
                .options(joinedload(Track.fingerprint))
                .where(Track.status != TrackStatus.ARCHIVED)
            )
            .unique()
            .scalars()
            .all()
        )
        members = [t for t in tracks if song_group_key(t) == group_key]
        if len(members) < 2:
            return []
        if not self._is_cross_fingerprint_group(members):
            return []
        return members
