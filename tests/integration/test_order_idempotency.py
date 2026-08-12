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


def test_duplicate_client_order_id_returns_same_order() -> None:
    reset_response = client.post(
        ("/api/v1/trading-control/kill-switch/deactivate"),
        json={"reason": "Idempotency reset"},
    )

    assert reset_response.status_code == 200

    enable_response = client.put(
        "/api/v1/trading-control/enabled",
        json={
            "enabled": True,
            "reason": ("Idempotency test"),
        },
    )

    assert enable_response.status_code == 200

    account_response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": ("Idempotency Account"),
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert account_response.status_code == 201

    account = account_response.json()

    symbol = f"ID{uuid4().hex[:6]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": ("Idempotency Instrument"),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201

    end_time = datetime.now(UTC)

    start_time = end_time - timedelta(days=5)

    ingestion_response = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": (start_time.isoformat()),
            "end_time": (end_time.isoformat()),
        },
    )

    assert ingestion_response.status_code == 201

    client_order_id = f"test-{uuid4()}"

    payload = {
        "account_id": account["id"],
        "client_order_id": (client_order_id),
        "symbol": symbol,
        "side": "buy",
        "order_type": "market",
        "quantity": 10,
        "time_in_force": "day",
    }

    first_response = client.post(
        "/api/v1/paper/orders",
        json=payload,
    )

    assert first_response.status_code == 201, first_response.text

    second_response = client.post(
        "/api/v1/paper/orders",
        json=payload,
    )

    assert second_response.status_code == 201, second_response.text

    first_order = first_response.json()

    second_order = second_response.json()

    assert first_order["id"] == second_order["id"]

    assert first_order["client_order_id"] == client_order_id
