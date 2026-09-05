from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def create_training_dataset() -> dict:
    symbol = f"T{uuid4().hex[:7]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Training Test Instrument",
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
            "start_time": ("2025-01-01T00:00:00Z"),
            "end_time": ("2026-03-15T00:00:00Z"),
        },
    )

    assert ingestion_response.status_code == 201

    feature_response = client.post(
        "/api/v1/features/generate",
        json={
            "feature_set_name": ("training_integration_features"),
            "description": ("Training integration features"),
            "symbol": symbol,
            "interval": "1d",
            "start_time": ("2025-01-01T00:00:00Z"),
            "end_time": ("2026-03-15T00:00:00Z"),
            "configuration": {
                "features": [
                    "simple_return",
                    "log_return",
                    "rolling_mean_20",
                    "rolling_std_20",
                    "rolling_volatility_20",
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
            "name": ("training_integration_dataset"),
            "feature_set_id": (feature_response.json()["feature_set_id"]),
            "symbol": symbol,
            "interval": "1d",
            "start_time": ("2025-01-01T00:00:00Z"),
            "end_time": ("2026-03-15T00:00:00Z"),
            "drop_missing_rows": True,
        },
    )

    assert dataset_response.status_code == 201
    assert Path(dataset_response.json()["storage_uri"]).exists()

    return dataset_response.json()


def test_train_classification_model() -> None:
    dataset = create_training_dataset()

    response = client.post(
        "/api/v1/training/runs",
        json={
            "dataset_id": (dataset["dataset_id"]),
            "model_type": ("logistic_regression"),
            "prediction_task": ("classification"),
            "feature_columns": [
                "simple_return",
                "log_return",
                "rolling_mean_20",
                "rolling_std_20",
                "rolling_volatility_20",
                "momentum_10",
                "rsi_14",
                "volume_change",
                "drawdown",
            ],
            "parameters": {
                "C": 1.0,
                "max_iter": 1000,
            },
            "number_of_splits": 3,
            "test_size": 10,
            "random_seed": 42,
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["training_run"]["status"] == "completed"

    assert body["model_artifact_id"]
    assert "accuracy" in body["metrics"]

    models_response = client.get("/api/v1/models")

    assert models_response.status_code == 200

    assert any(model["id"] == body["model_artifact_id"] for model in models_response.json())


def test_candidate_model_can_move_to_staging() -> None:
    dataset = create_training_dataset()

    training_response = client.post(
        "/api/v1/training/runs",
        json={
            "dataset_id": dataset["dataset_id"],
            "model_type": ("logistic_regression"),
            "prediction_task": ("classification"),
            "feature_columns": [
                "simple_return",
                "log_return",
                "rolling_mean_20",
                "momentum_10",
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
        json={"stage": "staging"},
    )

    assert stage_response.status_code == 200
    assert stage_response.json()["stage"] == "staging"
