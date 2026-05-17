from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.duplicate_group import DuplicateGroup
from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.setting import Setting
from app.models.track import Track
from app.schemas.duplicate import DuplicateResolveRequest
from app.services.duplicate_resolve_service import DuplicateResolveError, DuplicateResolveService


def _folder_settings(db_session: Session, tmp_path: Path) -> None:
    for key, sub in (
        ("watch_folder", "watch"),
        ("processing_folder", "processing"),
        ("ready_folder", "ready"),
        ("review_folder", "review"),
        ("duplicates_folder", "duplicates"),
        ("archive_folder", "archive"),
    ):
        db_session.add(Setting(key=key, value=str(tmp_path / sub)))
    db_session.commit()


def _duplicate_group(
    db_session: Session,
    hash_value: str,
    *,
    preferred_track_id: int | None = None,
) -> DuplicateGroup:
    group = DuplicateGroup(
        fingerprint_hash=hash_value,
        preferred_track_id=preferred_track_id,
    )
    db_session.add(group)
    db_session.flush()
    return group


def test_resolve_promotes_duplicate_keeper_and_archives_other(
    db_session: Session, tmp_path: Path
) -> None:
    _folder_settings(db_session, tmp_path)
    hash_value = "resolvehash01"

    ready_file = tmp_path / "ready" / "low.mp3"
    ready_file.parent.mkdir(parents=True)
    ready_file.write_bytes(b"low quality")

    dup_file = tmp_path / "duplicates" / hash_value / "high.mp3"
    dup_file.parent.mkdir(parents=True)
    dup_file.write_bytes(b"high quality")

    preferred = Track(
        source_path=str(tmp_path / "watch" / "low.mp3"),
        processing_path=None,
        final_path=str(ready_file),
        status=TrackStatus.READY,
        integrated_lufs=-14.0,
        tagged_at=None,
    )
    duplicate = Track(
        source_path=str(tmp_path / "watch" / "high.mp3"),
        processing_path=None,
        final_path=str(dup_file),
        status=TrackStatus.DUPLICATE,
        integrated_lufs=-14.0,
    )
    db_session.add_all([preferred, duplicate])
    db_session.commit()

    group = _duplicate_group(db_session, hash_value)
    for track in (preferred, duplicate):
        db_session.add(
            Fingerprint(
                track_id=track.id,
                duplicate_group_id=group.id,
                fingerprint_hash=hash_value,
            )
        )
    db_session.commit()

    with patch("app.services.duplicate_resolve_service.notify_pipeline_changed"):
        result = DuplicateResolveService(db_session).resolve(
            DuplicateResolveRequest(group_id=group.id, keep_track_id=duplicate.id)
        )

    db_session.refresh(preferred)
    db_session.refresh(duplicate)
    db_session.refresh(group)

    assert result.status == "ok"
    assert result.kept_track_id == duplicate.id
    assert result.archived_track_ids == [preferred.id]

    assert group.preferred_track_id == duplicate.id
    assert group.resolved_at is not None

    assert preferred.status == TrackStatus.ARCHIVED
    assert preferred.final_path is not None
    assert "archive" in preferred.final_path
    assert hash_value in preferred.final_path

    assert duplicate.status == TrackStatus.INGESTED
    assert duplicate.processing_path is not None
    assert Path(duplicate.processing_path).is_file()
    assert "processing" in duplicate.processing_path

    tag_jobs = (
        db_session.execute(
            select(Job).where(
                Job.job_type == JobType.TAG,
                Job.source_path == duplicate.source_path,
            )
        )
        .scalars()
        .all()
    )
    assert len(tag_jobs) == 1
    assert tag_jobs[0].status == JobStatus.PENDING


def test_resolve_keeps_ready_copy_archives_duplicate(db_session: Session, tmp_path: Path) -> None:
    _folder_settings(db_session, tmp_path)
    hash_value = "resolvehash02"

    ready_file = tmp_path / "ready" / "keeper.mp3"
    ready_file.parent.mkdir(parents=True)
    ready_file.write_bytes(b"keeper")

    dup_file = tmp_path / "duplicates" / hash_value / "extra.mp3"
    dup_file.parent.mkdir(parents=True)
    dup_file.write_bytes(b"extra")

    keeper = Track(
        source_path=str(tmp_path / "watch" / "keeper.mp3"),
        final_path=str(ready_file),
        status=TrackStatus.READY,
        integrated_lufs=-14.0,
        tagged_at=None,
    )
    extra = Track(
        source_path=str(tmp_path / "watch" / "extra.mp3"),
        final_path=str(dup_file),
        status=TrackStatus.DUPLICATE,
        integrated_lufs=-14.0,
    )
    db_session.add_all([keeper, extra])
    db_session.commit()

    group = _duplicate_group(db_session, hash_value)
    for track in (keeper, extra):
        db_session.add(
            Fingerprint(
                track_id=track.id,
                duplicate_group_id=group.id,
                fingerprint_hash=hash_value,
            )
        )
    db_session.commit()

    with patch("app.services.duplicate_resolve_service.notify_pipeline_changed"):
        result = DuplicateResolveService(db_session).resolve(
            DuplicateResolveRequest(group_id=group.id, keep_track_id=keeper.id)
        )

    db_session.refresh(keeper)
    db_session.refresh(extra)

    assert result.archived_track_ids == [extra.id]
    assert keeper.status == TrackStatus.READY
    assert keeper.final_path is not None
    assert Path(keeper.final_path).is_file()
    assert extra.status == TrackStatus.ARCHIVED


def test_resolve_rejects_unknown_group(db_session: Session) -> None:
    with pytest.raises(DuplicateResolveError) as exc:
        DuplicateResolveService(db_session).resolve(
            DuplicateResolveRequest(group_id=999, keep_track_id=1)
        )
    assert exc.value.status_code == 404


def test_resolve_rejects_archiving_keeper(db_session: Session, tmp_path: Path) -> None:
    _folder_settings(db_session, tmp_path)
    group = _duplicate_group(db_session, "hash422")
    track = Track(source_path=str(tmp_path / "a.mp3"), status=TrackStatus.DUPLICATE)
    db_session.add(track)
    db_session.commit()
    db_session.add(
        Fingerprint(
            track_id=track.id,
            duplicate_group_id=group.id,
            fingerprint_hash="hash422",
        )
    )
    db_session.commit()

    with pytest.raises(DuplicateResolveError) as exc:
        DuplicateResolveService(db_session).resolve(
            DuplicateResolveRequest(
                group_id=group.id,
                keep_track_id=track.id,
                archive_track_ids=[track.id],
            )
        )
    assert exc.value.status_code == 422
