from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import uuid4

from fastapi.testclient import (
    TestClient,
)

from finai.api.main import application


client = TestClient(application)


def create_account() -> dict:
    response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": ("Strategy Run Test Account"),
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_instrument_with_data() -> str:
    symbol = f"R{uuid4().hex[:7]}".upper()

    response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": ("Strategy Run Instrument"),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert response.status_code == 201, response.text

    end_time = datetime.now(UTC)

    start_time = end_time - timedelta(days=5)

    ingestion = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": (start_time.isoformat()),
            "end_time": (end_time.isoformat()),
        },
    )

    assert ingestion.status_code == 201, ingestion.text

    return symbol


def test_create_strategy_run() -> None:
    account = create_account()

    symbol = create_instrument_with_data()

    idempotency_key = f"run-{uuid4().hex}"

    response = client.post(
        "/api/v1/strategy/runs",
        json={
            "account_id": account["id"],
            "strategy_key": "default",
            "idempotency_key": (idempotency_key),
            "signals": [
                {
                    "symbol": symbol,
                    "side": "buy",
                    "confidence": 0.90,
                }
            ],
        },
    )

    assert response.status_code == 201, response.text

    result = response.json()

    assert result["signal_count"] == 1

    assert result["proposal_count"] == 1

    assert result["failed_count"] == 0

    assert result["status"] == ("completed")

    assert len(result["items"]) == 1

    item = result["items"][0]

    assert item["symbol"] == symbol

    assert item["proposal_id"] is not None

    assert item["status"] == "proposal_created"


def test_strategy_run_is_idempotent() -> None:
    account = create_account()

    symbol = create_instrument_with_data()

    key = f"idempotent-{uuid4().hex}"

    payload = {
        "account_id": account["id"],
        "strategy_key": "default",
        "idempotency_key": key,
        "signals": [
            {
                "symbol": symbol,
                "side": "buy",
                "confidence": 0.90,
            }
        ],
    }

    first = client.post(
        "/api/v1/strategy/runs",
        json=payload,
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/strategy/runs",
        json=payload,
    )

    assert second.status_code == 201, second.text

    assert first.json()["id"] == second.json()["id"]


def test_strategy_run_can_be_retrieved() -> None:
    account = create_account()

    symbol = create_instrument_with_data()

    create_response = client.post(
        "/api/v1/strategy/runs",
        json={
            "account_id": account["id"],
            "strategy_key": "default",
            "idempotency_key": (f"retrieve-{uuid4().hex}"),
            "signals": [
                {
                    "symbol": symbol,
                    "side": "buy",
                    "confidence": 0.90,
                }
            ],
        },
    )

    assert create_response.status_code == 201, create_response.text

    run_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/strategy/runs/{run_id}")

    assert get_response.status_code == 200, get_response.text

    result = get_response.json()

    assert result["id"] == run_id

    assert len(result["items"]) == 1
