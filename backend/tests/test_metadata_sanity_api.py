from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.track import Track


def test_metadata_sanity_check_endpoint_happy_path(
    client: TestClient, db_session: Session, tmp_path: Path
) -> None:
    track = Track(
        source_path=str(tmp_path / "polluted.mp3"),
        artist="Daft Punk",
        title="Daft Punk - One More Time",
        status=TrackStatus.INGESTED,
    )
    db_session.add(track)
    db_session.commit()

    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        response = client.post("/queue/metadata-sanity-check")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["scanned"] == 1
    assert data["flagged_artist_in_title"] == 1
    assert data["flagged_possible_swap"] == 0
    assert data["anomaly"] is True

    db_session.refresh(track)
    assert track.metadata_issue == "artist_in_title"
