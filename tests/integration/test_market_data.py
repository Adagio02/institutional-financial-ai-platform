from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_ingest_and_query_market_bars() -> None:
    symbol = f"M{uuid4().hex[:7]}".upper()

    create_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Market Data Test Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert create_response.status_code == 201

    ingest_response = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": "2026-01-01T00:00:00Z",
            "end_time": "2026-01-05T00:00:00Z",
        },
    )

    assert ingest_response.status_code == 201

    ingestion_result = ingest_response.json()

    assert ingestion_result["symbol"] == symbol
    assert ingestion_result["provider"] == "mock"
    assert ingestion_result["bars_received"] == 5
    assert ingestion_result["bars_persisted"] == 5

    bars_response = client.get(
        "/api/v1/market-data/bars",
        params={
            "symbol": symbol,
            "interval": "1d",
        },
    )

    assert bars_response.status_code == 200

    result = bars_response.json()

    assert result["symbol"] == symbol
    assert result["count"] == 5
    assert len(result["bars"]) == 5


def test_reingestion_is_idempotent() -> None:
    symbol = f"I{uuid4().hex[:7]}".upper()

    create_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Idempotency Test Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert create_response.status_code == 201

    payload = {
        "symbol": symbol,
        "interval": "1d",
        "start_time": "2026-02-01T00:00:00Z",
        "end_time": "2026-02-03T00:00:00Z",
    }

    first_response = client.post(
        "/api/v1/market-data/ingest",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/market-data/ingest",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    bars_response = client.get(
        "/api/v1/market-data/bars",
        params={
            "symbol": symbol,
            "interval": "1d",
        },
    )

    assert bars_response.status_code == 200
    assert bars_response.json()["count"] == 3
