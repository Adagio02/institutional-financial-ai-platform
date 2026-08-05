from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_create_and_complete_ingestion_job() -> None:
    symbol = f"J{uuid4().hex[:7]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Ingestion Job Test Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201

    job_response = client.post(
        "/api/v1/ingestion-jobs",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": "2026-03-01T00:00:00Z",
            "end_time": "2026-03-03T00:00:00Z",
        },
    )

    assert job_response.status_code == 202

    created_job = job_response.json()

    assert created_job["symbol"] == symbol
    assert created_job["status"] in {
        "pending",
        "running",
        "completed",
    }

    status_response = client.get(f"/api/v1/ingestion-jobs/{created_job['id']}")

    assert status_response.status_code == 200

    finished_job = status_response.json()

    assert finished_job["status"] == "completed"
    assert finished_job["received_count"] > 0
    assert finished_job["inserted_count"] > 0


def test_ingestion_job_requires_existing_instrument() -> None:
    response = client.post(
        "/api/v1/ingestion-jobs",
        json={
            "symbol": "DOESNOTEXIST",
            "interval": "1d",
            "start_time": "2026-03-01T00:00:00Z",
            "end_time": "2026-03-03T00:00:00Z",
        },
    )

    assert response.status_code == 404


def test_ingestion_job_rejects_invalid_range() -> None:
    response = client.post(
        "/api/v1/ingestion-jobs",
        json={
            "symbol": "INVALID",
            "interval": "1d",
            "start_time": "2026-03-03T00:00:00Z",
            "end_time": "2026-03-01T00:00:00Z",
        },
    )

    assert response.status_code == 422
