from unittest.mock import patch

from fastapi.testclient import TestClient

from finai.api.main import create_application


def test_liveness() -> None:
    app = create_application()

    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.json()["version"] == "0.2.0"


def test_readiness_when_database_is_ready() -> None:
    app = create_application()

    with patch(
        "finai.api.routes.health.check_database_connection",
        return_value=True,
    ):
        with TestClient(app) as client:
            response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_when_database_is_unavailable() -> None:
    app = create_application()

    with patch(
        "finai.api.routes.health.check_database_connection",
        return_value=False,
    ):
        with TestClient(app) as client:
            response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_request_id_is_returned() -> None:
    app = create_application()

    with TestClient(app) as client:
        response = client.get(
            "/health/live",
            headers={"X-Request-ID": "test-request-123"},
        )

    assert response.headers["X-Request-ID"] == "test-request-123"