from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.duplicate_group import DuplicateGroup
from app.models.enums import TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.setting import Setting
from app.models.track import Track


def _folder_settings(db_session: Session, tmp_path: Path) -> None:
    for key, sub in (
        ("processing_folder", "processing"),
        ("ready_folder", "ready"),
        ("review_folder", "review"),
        ("duplicates_folder", "duplicates"),
        ("archive_folder", "archive"),
    ):
        db_session.add(Setting(key=key, value=str(tmp_path / sub)))
    db_session.commit()


def test_resolve_endpoint_happy_path(
    client: TestClient, db_session: Session, tmp_path: Path
) -> None:
    _folder_settings(db_session, tmp_path)
    hash_value = "apihash01"

    dup_file = tmp_path / "duplicates" / hash_value / "copy.mp3"
    dup_file.parent.mkdir(parents=True)
    dup_file.write_bytes(b"dup")

    ready_file = tmp_path / "ready" / "other.mp3"
    ready_file.parent.mkdir(parents=True)
    ready_file.write_bytes(b"other")

    keeper = Track(
        source_path=str(tmp_path / "watch" / "copy.mp3"),
        final_path=str(dup_file),
        status=TrackStatus.DUPLICATE,
        integrated_lufs=-14.0,
    )
    other = Track(
        source_path=str(tmp_path / "watch" / "other.mp3"),
        final_path=str(ready_file),
        status=TrackStatus.READY,
        integrated_lufs=-14.0,
    )
    db_session.add_all([keeper, other])
    db_session.commit()

    group = DuplicateGroup(fingerprint_hash=hash_value)
    db_session.add(group)
    db_session.flush()
    for track in (keeper, other):
        db_session.add(
            Fingerprint(
                track_id=track.id,
                duplicate_group_id=group.id,
                fingerprint_hash=hash_value,
            )
        )
    db_session.commit()

    with patch("app.services.duplicate_resolve_service.notify_pipeline_changed"):
        response = client.post(
            "/duplicates/resolve",
            json={
                "group_id": group.id,
                "keep_track_id": keeper.id,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["kept_track_id"] == keeper.id
    assert data["archived_track_ids"] == [other.id]


def test_resolve_endpoint_unknown_group(client: TestClient) -> None:
    response = client.post(
        "/duplicates/resolve",
        json={"group_id": 99999, "keep_track_id": 1},
    )
    assert response.status_code == 404
