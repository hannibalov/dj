from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def test_list_song_duplicates_endpoint(
    client: TestClient, db_session: Session, tmp_path: Path
) -> None:
    tagged_at = datetime.now(UTC)
    t1 = Track(
        source_path=str(tmp_path / "a.mp3"),
        status=TrackStatus.REVIEW,
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-firestarter",
        tagged_at=tagged_at,
    )
    t2 = Track(
        source_path=str(tmp_path / "b.mp3"),
        status=TrackStatus.REVIEW,
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-firestarter",
        tagged_at=tagged_at,
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    db_session.add(Fingerprint(track_id=t1.id, fingerprint_hash="hash-a", duplicate_group_id=None))
    db_session.add(Fingerprint(track_id=t2.id, fingerprint_hash="hash-b", duplicate_group_id=None))
    db_session.commit()

    response = client.get("/duplicates/songs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["match_type"] == "musicbrainz"
    assert len(data[0]["members"]) == 2


def test_resolve_song_duplicate_endpoint(
    client: TestClient, db_session: Session, tmp_path: Path
) -> None:
    _folder_settings(db_session, tmp_path)
    tagged_at = datetime.now(UTC)

    review_file = tmp_path / "review" / "quiet.mp3"
    review_file.parent.mkdir(parents=True)
    review_file.write_bytes(b"quiet")

    loud_file = tmp_path / "review" / "loud.mp3"
    loud_file.write_bytes(b"loud")

    quiet = Track(
        source_path=str(tmp_path / "watch" / "quiet.mp3"),
        final_path=str(review_file),
        status=TrackStatus.REVIEW,
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-firestarter",
        tagged_at=tagged_at,
        integrated_lufs=-21.5,
    )
    loud = Track(
        source_path=str(tmp_path / "watch" / "loud.mp3"),
        final_path=str(loud_file),
        status=TrackStatus.REVIEW,
        artist="The Prodigy",
        title="Firestarter",
        musicbrainz_recording_id="mbid-firestarter",
        tagged_at=tagged_at,
        integrated_lufs=-8.7,
    )
    db_session.add_all([quiet, loud])
    db_session.commit()

    db_session.add(
        Fingerprint(track_id=quiet.id, fingerprint_hash="hash-quiet", duplicate_group_id=None)
    )
    db_session.add(
        Fingerprint(track_id=loud.id, fingerprint_hash="hash-loud", duplicate_group_id=None)
    )
    db_session.commit()

    list_response = client.get("/duplicates/songs")
    assert list_response.status_code == 200
    group_key = list_response.json()[0]["group_key"]

    with patch("app.services.song_duplicate_resolve_service.notify_pipeline_changed"):
        response = client.post(
            "/duplicates/songs/resolve",
            json={
                "group_key": group_key,
                "keep_track_id": loud.id,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["kept_track_id"] == loud.id
    assert data["archived_track_ids"] == [quiet.id]

    db_session.refresh(quiet)
    assert quiet.status == TrackStatus.ARCHIVED
