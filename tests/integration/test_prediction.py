from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def create_model_and_dataset() -> tuple[str, str, str]:
    symbol = f"P{uuid4().hex[:7]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Prediction Test Instrument",
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
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2026-03-15T00:00:00Z",
        },
    )

    assert ingestion_response.status_code == 201

    feature_response = client.post(
        "/api/v1/features/generate",
        json={
            "feature_set_name": ("prediction_test_features"),
            "description": ("Prediction integration features"),
            "symbol": symbol,
            "interval": "1d",
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2026-03-15T00:00:00Z",
            "configuration": {
                "features": [
                    "simple_return",
                    "log_return",
                    "rolling_mean_20",
                    "momentum_10",
                    "rsi_14",
                    "volume_change",
                    "drawdown",
                ]
            },
        },
    )

    assert feature_response.status_code == 201

    dataset_response = client.post(
        "/api/v1/datasets/build",
        json={
            "name": ("prediction_test_dataset"),
            "feature_set_id": (feature_response.json()["feature_set_id"]),
            "symbol": symbol,
            "interval": "1d",
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2026-03-15T00:00:00Z",
            "drop_missing_rows": True,
        },
    )

    assert dataset_response.status_code == 201

    dataset = dataset_response.json()

    assert Path(dataset["storage_uri"]).exists()

    training_response = client.post(
        "/api/v1/training/runs",
        json={
            "dataset_id": dataset["dataset_id"],
            "model_type": "logistic_regression",
            "prediction_task": "classification",
            "feature_columns": [
                "simple_return",
                "log_return",
                "rolling_mean_20",
                "momentum_10",
                "rsi_14",
                "volume_change",
                "drawdown",
            ],
            "parameters": {},
            "number_of_splits": 2,
            "test_size": 5,
            "random_seed": 42,
        },
    )

    assert training_response.status_code == 201

    model_id = training_response.json()["model_artifact_id"]

    stage_response = client.post(
        f"/api/v1/models/{model_id}/stage",
        json={
            "stage": "staging",
        },
    )

    assert stage_response.status_code == 200

    return (
        model_id,
        dataset["dataset_id"],
        symbol,
    )


def test_create_and_get_prediction() -> None:
    model_id, dataset_id, symbol = create_model_and_dataset()

    response = client.post(
        "/api/v1/predictions",
        json={
            "model_id": model_id,
            "dataset_id": dataset_id,
            "symbol": symbol,
            "forecast_horizon": "next_period",
        },
    )

    assert response.status_code == 201

    prediction = response.json()

    assert prediction["model_id"] == model_id
    assert prediction["dataset_id"] == dataset_id
    assert prediction["symbol"] == symbol
    assert prediction["status"] == "completed"
    assert len(prediction["model_hash"]) == 64

    get_response = client.get(f"/api/v1/predictions/{prediction['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == prediction["id"]


def test_create_prediction_explanation() -> None:
    model_id, dataset_id, symbol = create_model_and_dataset()

    prediction_response = client.post(
        "/api/v1/predictions",
        json={
            "model_id": model_id,
            "dataset_id": dataset_id,
            "symbol": symbol,
        },
    )

    assert prediction_response.status_code == 201

    prediction_id = prediction_response.json()["id"]

    explanation_response = client.post(f"/api/v1/predictions/{prediction_id}/explanations")

    assert explanation_response.status_code == 201

    explanation = explanation_response.json()

    assert explanation["prediction_id"] == prediction_id

    assert explanation["contributions"]
