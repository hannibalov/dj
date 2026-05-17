from fastapi.testclient import TestClient


def test_get_settings_returns_folder_paths(client: TestClient) -> None:
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert "watch_folder" in data
    assert "ready_folder" in data


def test_update_settings_persists_folders(client: TestClient) -> None:
    payload = {
        "folders": {
            "watch_folder": "/tmp/watch",
            "incoming_folder": "/tmp/incoming",
            "processing_folder": "/tmp/processing",
            "ready_folder": "/tmp/ready",
            "review_folder": "/tmp/review",
            "duplicates_folder": "/tmp/duplicates",
            "archive_folder": "/tmp/archive",
            "failed_folder": "/tmp/failed",
            "logs_folder": "/tmp/logs",
            "rekordbox_export_folder": "/tmp/rekordbox",
        }
    }
    response = client.put("/settings", json=payload)
    assert response.status_code == 200
    assert response.json()["watch_folder"] == "/tmp/watch"
