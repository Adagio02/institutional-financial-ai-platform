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


def enable_trading() -> None:
    client.post(
        ("/api/v1/trading-control/kill-switch/deactivate"),
        json={"reason": ("Version 1.1 test reset")},
    )

    response = client.put(
        "/api/v1/trading-control/enabled",
        json={
            "enabled": True,
            "reason": ("Version 1.1 test"),
        },
    )

    assert response.status_code == 200


def create_account() -> dict:
    response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": ("Version 1.1 Account"),
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_instrument() -> str:
    symbol = f"V{uuid4().hex[:7]}".upper()

    response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": ("Version 1.1 Instrument"),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert response.status_code == 201, response.text

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

    assert ingestion_response.status_code == 201, ingestion_response.text

    return symbol


def test_partial_fill_then_sync_to_filled() -> None:
    enable_trading()

    account = create_account()
    symbol = create_instrument()

    response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "client_order_id": (f"v11-{uuid4()}"),
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "time_in_force": "day",
        },
    )

    assert response.status_code == 201, response.text

    order = response.json()

    assert order["status"] in {
        "partially_filled",
        "filled",
    }

    assert order["broker_order_id"] is not None

    assert order["broker_name"] == "sandbox"

    if order["status"] == "partially_filled":
        assert order["remaining_quantity"] > 0

        sync_response = client.post((f"/api/v1/paper/execution/orders/{order['id']}/sync"))

        assert sync_response.status_code == 200, sync_response.text

        synced = sync_response.json()

        assert synced["status"] == "filled"

        assert synced["remaining_quantity"] == 0


def test_open_limit_order_can_be_cancelled() -> None:
    enable_trading()

    account = create_account()
    symbol = create_instrument()

    response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "client_order_id": (f"cancel-{uuid4()}"),
            "symbol": symbol,
            "side": "buy",
            "order_type": "limit",
            "quantity": 10,
            "limit_price": 0.01,
            "time_in_force": "day",
        },
    )

    assert response.status_code == 201, response.text

    order = response.json()

    assert order["status"] == "accepted"

    cancel_response = client.post((f"/api/v1/paper/execution/orders/{order['id']}/cancel"))

    assert cancel_response.status_code == 200, cancel_response.text

    cancelled = cancel_response.json()

    assert cancelled["status"] == "cancelled"

    assert cancelled["cancelled_at"] is not None
