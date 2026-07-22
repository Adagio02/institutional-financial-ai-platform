from fastapi.testclient import TestClient

from finai.api.main import app


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "alive"
    assert payload["service"] == "Institutional Financial AI Platform"
    assert payload["version"] == "0.2.0"


def test_readiness() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ready"
    assert payload["service"] == "Institutional Financial AI Platform"
    assert payload["version"] == "0.2.0"

    assert payload["dependencies"] == [
        {
            "name": "postgresql",
            "ready": True,
            "detail": None,
        }
    ]