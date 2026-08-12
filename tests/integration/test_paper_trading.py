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


def ensure_trading_enabled() -> None:
    deactivate_response = client.post(
        ("/api/v1/trading-control/kill-switch/deactivate"),
        json={"reason": ("Paper trading integration test reset")},
    )

    assert deactivate_response.status_code == 200, deactivate_response.text

    enable_response = client.put(
        "/api/v1/trading-control/enabled",
        json={
            "enabled": True,
            "reason": ("Paper trading integration test"),
        },
    )

    assert enable_response.status_code == 200, enable_response.text

    state = enable_response.json()

    assert state["trading_enabled"] is True

    assert state["kill_switch_active"] is False

    assert state["can_trade"] is True


def create_paper_account() -> dict:
    response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": ("Integration Paper Account"),
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_instrument_with_market_data() -> str:
    symbol = f"PT{uuid4().hex[:6]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": ("Paper Trading Instrument"),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201, instrument_response.text

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


def get_order_fills(
    order_id: str,
) -> list[dict]:
    response = client.get((f"/api/v1/paper/orders/{order_id}/fills"))

    assert response.status_code == 200, response.text

    return response.json()


def get_portfolio(
    account_id: str,
) -> dict:
    response = client.get((f"/api/v1/paper/portfolio/{account_id}"))

    assert response.status_code == 200, response.text

    return response.json()


def sync_order(
    order_id: str,
) -> dict:
    response = client.post((f"/api/v1/paper/execution/orders/{order_id}/sync"))

    assert response.status_code == 200, response.text

    return response.json()


def test_create_account_and_market_order() -> None:
    ensure_trading_enabled()

    account = create_paper_account()

    symbol = create_instrument_with_market_data()

    client_order_id = f"paper-{uuid4()}"

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "client_order_id": (client_order_id),
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 201, order_response.text

    order = order_response.json()

    assert order["client_order_id"] == client_order_id

    assert order["symbol"] == symbol

    assert order["status"] in {
        "partially_filled",
        "filled",
    }

    assert order["broker_name"] == "sandbox"

    assert order["broker_order_id"] is not None

    assert order["submitted_at"] is not None

    assert order["reference_price"] is not None

    assert order["reference_price"] > 0

    assert order["reference_price_timestamp"] is not None

    assert order["reference_price_provider"] is not None

    assert order["filled_quantity"] > 0

    assert order["filled_quantity"] <= order["quantity"]

    assert order["remaining_quantity"] == (order["quantity"] - order["filled_quantity"])

    assert order["average_fill_price"] is not None

    initial_fills = get_order_fills(order["id"])

    assert len(initial_fills) >= 1

    initial_fill_quantity = sum(fill["quantity"] for fill in initial_fills)

    assert initial_fill_quantity == order["filled_quantity"]

    for fill in initial_fills:
        assert fill["quantity"] > 0

        assert fill["price"] > 0

        assert fill["notional"] > 0

        assert fill["commission"] >= 0

        assert fill["slippage_cost"] >= 0

    initial_portfolio = get_portfolio(account["id"])

    matching_positions = [
        position for position in initial_portfolio["positions"] if position["symbol"] == symbol
    ]

    assert len(matching_positions) == 1

    position = matching_positions[0]

    assert position["quantity"] == order["filled_quantity"]

    assert initial_portfolio["cash"] < account["initial_cash"]

    final_order = order

    if order["status"] == "partially_filled":
        final_order = sync_order(order["id"])

        assert final_order["status"] == "filled"

        assert final_order["filled_quantity"] == final_order["quantity"]

        assert final_order["remaining_quantity"] == 0

        assert final_order["last_synced_at"] is not None

    final_fills = get_order_fills(final_order["id"])

    total_fill_quantity = sum(fill["quantity"] for fill in final_fills)

    assert total_fill_quantity == final_order["filled_quantity"]

    final_portfolio = get_portfolio(account["id"])

    final_matching_positions = [
        position for position in final_portfolio["positions"] if position["symbol"] == symbol
    ]

    assert len(final_matching_positions) == 1

    final_position = final_matching_positions[0]

    assert final_position["quantity"] == final_order["filled_quantity"]


def test_oversized_order_is_rejected() -> None:
    ensure_trading_enabled()

    account = create_paper_account()

    symbol = create_instrument_with_market_data()

    client_order_id = f"risk-{uuid4()}"

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "client_order_id": (client_order_id),
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 100_000,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 201, order_response.text

    order = order_response.json()

    assert order["status"] == "rejected"

    assert order["rejection_reason"] is not None

    assert order["filled_quantity"] == 0

    assert order["remaining_quantity"] == order["quantity"]

    assert order["reference_price"] is not None

    assert order["reference_price_timestamp"] is not None

    assert order["broker_order_id"] is None

    fills = get_order_fills(order["id"])

    assert fills == []


def test_client_cannot_supply_reference_price() -> None:
    ensure_trading_enabled()

    account = create_paper_account()

    symbol = create_instrument_with_market_data()

    response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "client_order_id": (f"injection-{uuid4()}"),
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "reference_price": 0.01,
            "time_in_force": "day",
        },
    )

    assert response.status_code == 422


def test_order_requires_server_market_data() -> None:
    ensure_trading_enabled()

    account = create_paper_account()

    symbol = f"ND{uuid4().hex[:6]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": ("No Data Instrument"),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201, instrument_response.text

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "client_order_id": (f"nodata-{uuid4()}"),
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 404, order_response.text

    detail = order_response.json()["detail"]

    assert "No market data" in detail


def test_duplicate_client_order_id_is_idempotent() -> None:
    ensure_trading_enabled()

    account = create_paper_account()

    symbol = create_instrument_with_market_data()

    client_order_id = f"idempotent-{uuid4()}"

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

    first_order = first_response.json()

    fills_before = get_order_fills(first_order["id"])

    second_response = client.post(
        "/api/v1/paper/orders",
        json=payload,
    )

    assert second_response.status_code == 201, second_response.text

    second_order = second_response.json()

    assert first_order["id"] == second_order["id"]

    assert second_order["client_order_id"] == client_order_id

    fills_after = get_order_fills(second_order["id"])

    assert len(fills_after) == len(fills_before)


def test_non_marketable_limit_order_can_be_cancelled() -> None:
    ensure_trading_enabled()

    account = create_paper_account()

    symbol = create_instrument_with_market_data()

    order_response = client.post(
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

    assert order_response.status_code == 201, order_response.text

    order = order_response.json()

    assert order["status"] == "accepted"

    assert order["filled_quantity"] == 0

    assert order["remaining_quantity"] == order["quantity"]

    assert order["broker_order_id"] is not None

    cancel_response = client.post((f"/api/v1/paper/execution/orders/{order['id']}/cancel"))

    assert cancel_response.status_code == 200, cancel_response.text

    cancelled = cancel_response.json()

    assert cancelled["status"] == "cancelled"

    assert cancelled["cancelled_at"] is not None

    assert cancelled["remaining_quantity"] == order["quantity"]


def test_filled_order_cannot_be_cancelled() -> None:
    ensure_trading_enabled()

    account = create_paper_account()

    symbol = create_instrument_with_market_data()

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "client_order_id": (f"terminal-{uuid4()}"),
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 201, order_response.text

    order = order_response.json()

    if order["status"] == "partially_filled":
        order = sync_order(order["id"])

    assert order["status"] == "filled"

    cancel_response = client.post((f"/api/v1/paper/execution/orders/{order['id']}/cancel"))

    assert cancel_response.status_code == 409, cancel_response.text

    detail = cancel_response.json()["detail"]

    assert "cannot be cancelled" in detail.lower()
