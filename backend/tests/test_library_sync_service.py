from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.setting import Setting
from app.models.track import Track
from app.services.library_sync_service import LibrarySyncService


def _set_folders(db_session: Session, tmp_path: Path) -> None:
    folders = {
        "watch_folder": tmp_path / "watch",
        "incoming_folder": tmp_path / "incoming",
        "processing_folder": tmp_path / "processing",
        "ready_folder": tmp_path / "ready",
        "review_folder": tmp_path / "review",
        "duplicates_folder": tmp_path / "duplicates",
        "archive_folder": tmp_path / "archive",
        "failed_folder": tmp_path / "failed",
        "logs_folder": tmp_path / "logs",
        "rekordbox_export_folder": tmp_path / "rekordbox",
    }
    for key, value in folders.items():
        value.mkdir(parents=True, exist_ok=True)
        db_session.add(Setting(key=key, value=str(value)))
    db_session.commit()


def test_library_sync_enqueues_new_watch_files(db_session: Session, tmp_path: Path) -> None:
    _set_folders(db_session, tmp_path)
    watch_file = tmp_path / "watch" / "New Track - Artist.mp3"
    watch_file.write_bytes(b"x")

    result = LibrarySyncService(db_session).sync_library()

    assert result.enqueued == 1
    assert result.skipped == 0
    assert result.orphan_files == 0


def test_library_sync_repairs_stale_final_path(db_session: Session, tmp_path: Path) -> None:
    _set_folders(db_session, tmp_path)
    basename = "Song - Artist (Original Mix).mp3"
    ready_file = tmp_path / "ready" / basename
    ready_file.write_bytes(b"x")
    stale_path = tmp_path / "processing" / basename
    track = Track(
        source_path=str(tmp_path / "watch" / "Song - Artist.mp3"),
        final_path=str(stale_path),
        artist="Artist",
        title="Song",
        status=TrackStatus.READY,
        tagged_at=datetime.now(UTC),
    )
    db_session.add(track)
    db_session.commit()

    result = LibrarySyncService(db_session).sync_library()
    db_session.refresh(track)

    assert result.paths_repaired == 1
    assert track.final_path == str(ready_file)


def test_library_sync_updates_reversed_metadata_from_filename(
    db_session: Session, tmp_path: Path
) -> None:
    _set_folders(db_session, tmp_path)
    ready_file = tmp_path / "ready" / "Wonderwall - Oaisis (Original Mix).mp3"
    ready_file.write_bytes(b"x")
    other_file = tmp_path / "ready" / "Champagne Supernova - Oasis (Original Mix).mp3"
    other_file.write_bytes(b"y")
    db_session.add(
        Track(
            source_path=str(tmp_path / "watch" / "Wonderwall - Oaisis.mp3"),
            final_path=str(ready_file),
            artist="Wonderwall",
            title="Oaisis",
            status=TrackStatus.READY,
            tagged_at=datetime.now(UTC),
        )
    )
    db_session.add(
        Track(
            source_path=str(tmp_path / "watch" / "other.mp3"),
            final_path=str(tmp_path / "ready" / "Champagne Supernova - Oasis (Original Mix).mp3"),
            artist="Oasis",
            title="Champagne Supernova",
            status=TrackStatus.READY,
            tagged_at=datetime.now(UTC),
            tag_confidence=0.94,
        )
    )
    db_session.commit()

    result = LibrarySyncService(db_session).sync_library()
    updated = db_session.get(Track, 1)

    assert result.metadata_updated == 1
    assert updated is not None
    assert updated.artist == "Oasis"
    assert updated.title == "Wonderwall"


def test_library_sync_marks_missing_files_failed(db_session: Session, tmp_path: Path) -> None:
    _set_folders(db_session, tmp_path)
    track = Track(
        source_path=str(tmp_path / "watch" / "gone.mp3"),
        final_path=str(tmp_path / "ready" / "gone.mp3"),
        status=TrackStatus.READY,
    )
    db_session.add(track)
    db_session.commit()

    result = LibrarySyncService(db_session).sync_library()
    db_session.refresh(track)

    assert result.missing_files == 1
    assert track.status == TrackStatus.FAILED
