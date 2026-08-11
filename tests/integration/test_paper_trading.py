from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_create_account_and_market_order() -> None:
    account_response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": "Integration Paper Account",
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert account_response.status_code == 201

    account = account_response.json()

    symbol = f"PT{uuid4().hex[:6]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Paper Trading Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "reference_price": 100.0,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 201

    order = order_response.json()

    assert order["status"] == "filled"
    assert order["filled_quantity"] == 10
    assert order["average_fill_price"] is not None

    fill_response = client.get(f"/api/v1/paper/orders/{order['id']}/fills")

    assert fill_response.status_code == 200
    assert len(fill_response.json()) == 1

    portfolio_response = client.get(f"/api/v1/paper/portfolio/{account['id']}")

    assert portfolio_response.status_code == 200

    portfolio = portfolio_response.json()

    assert len(portfolio["positions"]) == 1
    assert portfolio["positions"][0]["symbol"] == symbol


def test_oversized_order_is_rejected() -> None:
    account_response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": "Risk Test Account",
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert account_response.status_code == 201

    account = account_response.json()

    symbol = f"RK{uuid4().hex[:6]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Risk Test Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 1000,
            "reference_price": 100.0,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 201

    order = order_response.json()

    assert order["status"] == "rejected"
    assert order["rejection_reason"]
