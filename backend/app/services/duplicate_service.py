from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.duplicate_group import DuplicateGroup
from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.track import Track
from app.schemas.duplicate import DuplicateGroupMember, DuplicateGroupResponse
from app.utils.audio_format import get_format_info


class DuplicateService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_groups(self) -> list[DuplicateGroupResponse]:
        groups = (
            self._db.execute(
                select(DuplicateGroup)
                .where(DuplicateGroup.resolved_at.is_(None))
                .order_by(DuplicateGroup.id)
            )
            .scalars()
            .all()
        )
        result: list[DuplicateGroupResponse] = []
        for group in groups:
            members = self._members_for_group(group)
            active_members = [m for m in members if m.status != TrackStatus.ARCHIVED]
            if len(active_members) < 2:
                continue
            result.append(
                DuplicateGroupResponse(
                    id=group.id,
                    fingerprint_hash=group.fingerprint_hash,
                    preferred_track_id=group.preferred_track_id,
                    members=active_members,
                )
            )
        return result

    def _members_for_group(self, group: DuplicateGroup) -> list[DuplicateGroupMember]:
        rows = self._db.execute(
            select(Track, Fingerprint)
            .join(Fingerprint, Fingerprint.track_id == Track.id)
            .where(Fingerprint.duplicate_group_id == group.id)
            .order_by(Track.id)
        ).all()
        members: list[DuplicateGroupMember] = []
        for track, fp in rows:
            path = self._member_path(track)
            ext = path.suffix.lower() if path else ""
            bitrate = None
            if path and path.is_file():
                bitrate = get_format_info(path).bitrate_kbps
            members.append(
                DuplicateGroupMember(
                    track_id=track.id,
                    status=track.status,
                    source_path=track.source_path,
                    final_path=track.final_path,
                    fingerprint_hash=fp.fingerprint_hash,
                    duration_seconds=fp.duration_seconds,
                    format_extension=ext or None,
                    bitrate_kbps=bitrate,
                    artist=track.artist,
                    title=track.title,
                    integrated_lufs=track.integrated_lufs,
                )
            )
        return members

    @staticmethod
    def _member_path(track: Track) -> Path | None:
        if track.final_path:
            p = Path(track.final_path)
            if p.is_file():
                return p
        if track.processing_path:
            p = Path(track.processing_path)
            if p.is_file():
                return p
        return Path(track.source_path) if track.source_path else None
