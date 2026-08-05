import struct
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.metadata.musicbrainz_lookup import RecordingGenreInfo
from app.models.enums import TrackStatus
from app.models.setting import Setting
from app.models.track import Track


def _minimal_wav(path: Path) -> None:
    data = b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt " + struct.pack("<I", 16)
    data += struct.pack("<HHIIHH", 1, 1, 44100, 88200, 2, 16)
    data += b"data" + struct.pack("<I", 0)
    path.write_bytes(data)


def _naming_template(db_session: Session) -> None:
    db_session.add(Setting(key="naming_template", value="{title} - {artist} ({mix}){ext}"))
    db_session.commit()


def _track_with_file(tmp_path: Path, name: str, *, artist: str, title: str) -> Track:
    wav = tmp_path / "processing" / name
    wav.parent.mkdir(parents=True, exist_ok=True)
    _minimal_wav(wav)
    return Track(
        source_path=str(tmp_path / "watch" / name),
        processing_path=str(wav),
        status=TrackStatus.REVIEW,
        artist=artist,
        title=title,
    )


def test_swap_artist_title_endpoint(
    client: TestClient, db_session: Session, tmp_path: Path
) -> None:
    track = _track_with_file(tmp_path, "swap.wav", artist="Wonderwall", title="Oasis")
    db_session.add(track)
    db_session.commit()
    _naming_template(db_session)

    with patch("app.services.track_metadata_service.notify_pipeline_changed"):
        response = client.post(f"/tracks/{track.id}/swap-artist-title")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["track"]["artist"] == "Oasis"
    assert body["track"]["title"] == "Wonderwall"


def test_swap_artist_title_endpoint_missing_track(client: TestClient) -> None:
    response = client.post("/tracks/999999/swap-artist-title")
    assert response.status_code == 400


def test_rename_artist_endpoint(client: TestClient, db_session: Session, tmp_path: Path) -> None:
    track_a = _track_with_file(tmp_path, "a.wav", artist="Daft Punk", title="One More Time")
    track_b = _track_with_file(tmp_path, "b.wav", artist="daft punk", title="Around the World")
    track_c = _track_with_file(tmp_path, "c.wav", artist="Justice", title="D.A.N.C.E.")
    db_session.add_all([track_a, track_b, track_c])
    db_session.commit()
    _naming_template(db_session)

    with (
        patch("app.services.track_metadata_service.notify_pipeline_changed"),
        patch(
            "app.services.track_metadata_service.resolve_track_genres",
            return_value=RecordingGenreInfo(None, None, None),
        ),
    ):
        response = client.post(
            "/tracks/rename-artist",
            json={"old_artist": "Daft Punk", "new_artist": "Daft Punk Corrected"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["matched"] == 2
    assert body["updated"] == 2

    db_session.refresh(track_c)
    assert track_c.artist == "Justice"


def test_rename_artist_endpoint_requires_names(client: TestClient) -> None:
    response = client.post(
        "/tracks/rename-artist",
        json={"old_artist": "", "new_artist": "Someone"},
    )
    assert response.status_code == 422
