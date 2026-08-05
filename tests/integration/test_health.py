from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_live_health() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready_health() -> None:
    response = client.get("/health/ready")

    assert response.status_code in {200, 503}
