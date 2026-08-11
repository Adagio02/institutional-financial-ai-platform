from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def create_paper_account() -> dict:
    response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": "Integration Paper Account",
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def create_instrument_with_market_data() -> str:
    symbol = (
        f"PT{uuid4().hex[:6]}"
        .upper()
    )

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

    assert (
        instrument_response.status_code
        == 201
    ), instrument_response.text

    end_time = datetime.now(UTC)

    start_time = (
        end_time
        - timedelta(days=5)
    )

    ingestion_response = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": (
                start_time.isoformat()
            ),
            "end_time": (
                end_time.isoformat()
            ),
        },
    )

    assert (
        ingestion_response.status_code
        == 201
    ), ingestion_response.text

    return symbol


def test_create_account_and_market_order() -> None:
    account = create_paper_account()

    symbol = (
        create_instrument_with_market_data()
    )

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 201, (
        order_response.text
    )

    order = order_response.json()

    assert order["status"] == "filled"

    assert (
        order["filled_quantity"]
        == 10
    )

    assert (
        order["average_fill_price"]
        is not None
    )

    assert (
        order["reference_price"]
        is not None
    )

    assert (
        order["reference_price"]
        > 0
    )

    assert (
        order[
            "reference_price_timestamp"
        ]
        is not None
    )

    assert (
        order[
            "reference_price_provider"
        ]
        is not None
    )

    assert (
        order["average_fill_price"]
        >= order["reference_price"]
    )

    fill_response = client.get(
        f"/api/v1/paper/orders/"
        f"{order['id']}/fills"
    )

    assert (
        fill_response.status_code
        == 200
    )

    fills = fill_response.json()

    assert len(fills) == 1

    fill = fills[0]

    assert fill["quantity"] == 10
    assert fill["price"] > 0
    assert fill["notional"] > 0
    assert fill["commission"] >= 0
    assert fill["slippage_cost"] >= 0

    portfolio_response = client.get(
        f"/api/v1/paper/portfolio/"
        f"{account['id']}"
    )

    assert (
        portfolio_response.status_code
        == 200
    )

    portfolio = (
        portfolio_response.json()
    )

    assert len(
        portfolio["positions"]
    ) == 1

    position = (
        portfolio["positions"][0]
    )

    assert (
        position["symbol"]
        == symbol
    )

    assert (
        position["quantity"]
        == 10
    )

    assert (
        portfolio["cash"]
        < account["initial_cash"]
    )


def test_oversized_order_is_rejected() -> None:
    account = create_paper_account()

    symbol = (
        create_instrument_with_market_data()
    )

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 100_000,
            "time_in_force": "day",
        },
    )

    assert order_response.status_code == 201, (
        order_response.text
    )

    order = order_response.json()

    assert (
        order["status"]
        == "rejected"
    )

    assert (
        order["rejection_reason"]
        is not None
    )

    assert (
        order["reference_price"]
        is not None
    )

    assert (
        order[
            "reference_price_timestamp"
        ]
        is not None
    )


def test_client_cannot_supply_reference_price() -> None:
    account = create_paper_account()

    symbol = (
        create_instrument_with_market_data()
    )

    response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
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
    account = create_paper_account()

    symbol = (
        f"ND{uuid4().hex[:6]}"
        .upper()
    )

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "No Data Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert (
        instrument_response.status_code
        == 201
    ), instrument_response.text

    order_response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": account["id"],
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "time_in_force": "day",
        },
    )

    assert (
        order_response.status_code
        == 404
    ), order_response.text

    detail = (
        order_response.json()[
            "detail"
        ]
    )

    assert (
        "No market data"
        in detail
    )