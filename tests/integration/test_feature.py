from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_generate_and_list_features() -> None:
    symbol = f"F{uuid4().hex[:7]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Feature Test Instrument",
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
            "feature_set_name": ("integration_test_features"),
            "description": ("Integration test feature set"),
            "symbol": symbol,
            "interval": "1d",
            "start_time": ("2026-01-01T00:00:00Z"),
            "end_time": ("2026-03-15T00:00:00Z"),
            "configuration": {
                "features": [
                    "simple_return",
                    "log_return",
                    "rolling_mean_20",
                    "rolling_volatility_20",
                    "momentum_10",
                    "rsi_14",
                    "atr_14",
                    "macd",
                    "macd_signal",
                    "macd_histogram",
                    "volume_change",
                    "drawdown",
                ]
            },
        },
    )

    assert feature_response.status_code == 201

    body = feature_response.json()

    assert body["values_persisted"] > 0
    assert body["version"] >= 1

    list_response = client.get("/api/v1/features/sets")

    assert list_response.status_code == 200

    feature_sets = list_response.json()

    assert any(item["id"] == body["feature_set_id"] for item in feature_sets)
