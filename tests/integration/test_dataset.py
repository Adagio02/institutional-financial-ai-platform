from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_build_and_get_dataset() -> None:
    symbol = f"D{uuid4().hex[:7]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Dataset Test Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201

    ingestion_response = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": ("2026-01-01T00:00:00Z"),
            "end_time": ("2026-03-15T00:00:00Z"),
        },
    )

    assert ingestion_response.status_code == 201

    feature_response = client.post(
        "/api/v1/features/generate",
        json={
            "feature_set_name": ("dataset_test_features"),
            "description": ("Dataset integration test"),
            "symbol": symbol,
            "interval": "1d",
            "start_time": ("2026-01-01T00:00:00Z"),
            "end_time": ("2026-03-15T00:00:00Z"),
            "configuration": {
                "features": [
                    "simple_return",
                    "rolling_mean_20",
                    "rolling_volatility_20",
                    "momentum_10",
                ]
            },
        },
    )

    assert feature_response.status_code == 201

    feature_set_id = feature_response.json()["feature_set_id"]

    dataset_response = client.post(
        "/api/v1/datasets/build",
        json={
            "name": ("integration_test_dataset"),
            "feature_set_id": feature_set_id,
            "symbol": symbol,
            "interval": "1d",
            "start_time": ("2026-01-01T00:00:00Z"),
            "end_time": ("2026-03-15T00:00:00Z"),
            "drop_missing_rows": True,
        },
    )

    assert dataset_response.status_code == 201

    dataset = dataset_response.json()

    assert dataset["row_count"] > 0
    assert len(dataset["schema_hash"]) == 64
    assert len(dataset["content_hash"]) == 64
    assert Path(dataset["storage_uri"]).exists()

    get_response = client.get(f"/api/v1/datasets/{dataset['dataset_id']}")

    assert get_response.status_code == 200

    stored_dataset = get_response.json()

    assert stored_dataset["status"] == "completed"
    assert stored_dataset["content_hash"] == dataset["content_hash"]
