from fastapi.testclient import TestClient


def test_queue_empty_summary(client: TestClient) -> None:
    response = client.get("/queue")
    assert response.status_code == 200
    data = response.json()
    assert data["pending"] == 0
    assert data["jobs"] == []
