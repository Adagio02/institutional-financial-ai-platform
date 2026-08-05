from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_metrics_endpoint() -> None:
    client.get("/health/live")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.text

    metrics_text = response.text.lower()

    assert "http_requests" in metrics_text or "http_request" in metrics_text
