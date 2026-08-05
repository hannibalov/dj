from pathlib import Path

from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.setting import Setting
from app.models.track import Track
from app.services.duplicate_service import DuplicateService


def test_list_groups_returns_multi_member_groups_only(db_session: Session, tmp_path: Path) -> None:
    db_session.add(Setting(key="duplicates_folder", value=str(tmp_path / "duplicates")))
    t1 = Track(source_path=str(tmp_path / "a.mp3"), status=TrackStatus.DUPLICATE)
    t2 = Track(source_path=str(tmp_path / "b.mp3"), status=TrackStatus.READY)
    db_session.add_all([t1, t2])
    db_session.commit()

    from app.models.duplicate_group import DuplicateGroup

    group = DuplicateGroup(fingerprint_hash="hashgroup1")
    db_session.add(group)
    db_session.flush()

    db_session.add(
        Fingerprint(track_id=t1.id, duplicate_group_id=group.id, fingerprint_hash="hashgroup1")
    )
    db_session.add(
        Fingerprint(track_id=t2.id, duplicate_group_id=group.id, fingerprint_hash="hashgroup1")
    )
    db_session.commit()

    groups = DuplicateService(db_session).list_groups()
    assert len(groups) == 1
    assert groups[0].fingerprint_hash == "hashgroup1"
    assert len(groups[0].members) == 2


def test_list_groups_excludes_resolved_groups(db_session: Session, tmp_path: Path) -> None:
    db_session.add(Setting(key="duplicates_folder", value=str(tmp_path / "duplicates")))
    t1 = Track(source_path=str(tmp_path / "a.mp3"), status=TrackStatus.DUPLICATE)
    t2 = Track(source_path=str(tmp_path / "b.mp3"), status=TrackStatus.READY)
    db_session.add_all([t1, t2])
    db_session.commit()

    from datetime import UTC, datetime

    from app.models.duplicate_group import DuplicateGroup

    group = DuplicateGroup(
        fingerprint_hash="resolvedhash",
        preferred_track_id=t2.id,
        resolved_at=datetime.now(UTC),
    )
    db_session.add(group)
    db_session.flush()

    for track in (t1, t2):
        db_session.add(
            Fingerprint(
                track_id=track.id,
                duplicate_group_id=group.id,
                fingerprint_hash="resolvedhash",
            )
        )
    db_session.commit()

    assert DuplicateService(db_session).list_groups() == []


def test_list_groups_excludes_archived_members_from_count(
    db_session: Session, tmp_path: Path
) -> None:
    db_session.add(Setting(key="duplicates_folder", value=str(tmp_path / "duplicates")))
    active = Track(source_path=str(tmp_path / "a.mp3"), status=TrackStatus.DUPLICATE)
    archived = Track(source_path=str(tmp_path / "b.mp3"), status=TrackStatus.ARCHIVED)
    db_session.add_all([active, archived])
    db_session.commit()

    from app.models.duplicate_group import DuplicateGroup

    group = DuplicateGroup(fingerprint_hash="oneactive")
    db_session.add(group)
    db_session.flush()

    for track in (active, archived):
        db_session.add(
            Fingerprint(
                track_id=track.id,
                duplicate_group_id=group.id,
                fingerprint_hash="oneactive",
            )
        )
    db_session.commit()

    assert DuplicateService(db_session).list_groups() == []
