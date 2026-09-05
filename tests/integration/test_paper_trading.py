from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(
    application
)


def create_account() -> dict:
    response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": (
                "Paper-"
                + uuid4().hex[:8]
            ),
            "initial_cash": 100_000.0,
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def ensure_trading_enabled(
    account_id: str,
) -> None:
    reset_response = client.post(
        (
            "/api/v1/trading-controls/"
            f"{account_id}/reset-circuit-breaker"
        ),
    )

    assert reset_response.status_code == 200, (
        reset_response.text
    )

    resume_response = client.post(
        (
            "/api/v1/trading-controls/"
            f"{account_id}/resume"
        ),
    )

    assert resume_response.status_code == 200, (
        resume_response.text
    )

    enabled_response = client.post(
        (
            "/api/v1/trading-controls/"
            f"{account_id}/enabled"
        ),
        json={
            "enabled": True,
        },
    )

    assert enabled_response.status_code == 200, (
        enabled_response.text
    )


def create_instrument_with_data() -> str:
    symbol = (
        "T"
        + uuid4().hex[:7]
    ).upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": (
                "Paper Trading Test "
                + symbol
            ),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert (
        instrument_response.status_code
        == 201
    ), instrument_response.text

    now = datetime.now(UTC)

    start_time = (
        now
        - timedelta(days=7)
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
                now.isoformat()
            ),
        },
    )

    assert (
        ingestion_response.status_code
        == 201
    ), ingestion_response.text

    return symbol


def create_market_order(
    *,
    account_id: str,
    symbol: str,
    quantity: float = 1.0,
    side: str = "buy",
    client_order_id: str | None = None,
):
    payload = {
        "account_id": account_id,
        "symbol": symbol,
        "side": side,
        "order_type": "market",
        "quantity": quantity,
        "time_in_force": "day",
    }

    if client_order_id is not None:
        payload["client_order_id"] = (
            client_order_id
        )

    return client.post(
        "/api/v1/paper/orders",
        json=payload,
    )


def test_create_account_and_market_order() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        create_instrument_with_data()
    )

    response = create_market_order(
        account_id=account["id"],
        symbol=symbol,
        quantity=1.0,
    )

    assert response.status_code == 201, (
        response.text
    )

    order = response.json()

    assert (
        order["account_id"]
        == account["id"]
    )

    assert (
        order["symbol"]
        == symbol
    )

    assert (
        order["side"]
        == "buy"
    )

    assert (
        order["quantity"]
        == 1.0
    )

    assert order["status"] in {
        "filled",
        "partially_filled",
        "accepted",
        "open",
        "pending",
    }


def test_oversized_order_is_rejected() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = create_instrument_with_data()

    response = create_market_order(
        account_id=account["id"],
        symbol=symbol,
        quantity=1_000_000.0,
    )

    assert response.status_code == 409, (
        response.text
    )

    detail = response.json()["detail"]

    assert (
        "Pre-trade risk rejected order"
        in detail
    )

    assert (
        "Order quantity exceeds"
        in detail
    )


def test_client_cannot_supply_reference_price() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        create_instrument_with_data()
    )

    response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": (
                account["id"]
            ),
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "quantity": 1.0,
            "time_in_force": "day",
            "reference_price": 1.0,
        },
    )

    assert response.status_code in {
        400,
        422,
    }


def test_order_requires_server_market_data() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        "N"
        + uuid4().hex[:7]
    ).upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": (
                "No Market Data "
                + symbol
            ),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert (
        instrument_response.status_code
        == 201
    ), instrument_response.text

    response = create_market_order(
        account_id=account["id"],
        symbol=symbol,
        quantity=1.0,
    )

    assert response.status_code in {
        404,
        409,
        422,
    }


def test_duplicate_client_order_id_is_idempotent() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        create_instrument_with_data()
    )

    client_order_id = (
        "paper-"
        + uuid4().hex
    )

    first_response = (
        create_market_order(
            account_id=account["id"],
            symbol=symbol,
            quantity=1.0,
            client_order_id=(
                client_order_id
            ),
        )
    )

    assert (
        first_response.status_code
        == 201
    ), first_response.text

    second_response = (
        create_market_order(
            account_id=account["id"],
            symbol=symbol,
            quantity=1.0,
            client_order_id=(
                client_order_id
            ),
        )
    )

    assert second_response.status_code in {
        200,
        201,
    }, second_response.text

    first_order = (
        first_response.json()
    )

    second_order = (
        second_response.json()
    )

    assert (
        second_order["id"]
        == first_order["id"]
    )


def test_non_marketable_limit_order_can_be_cancelled() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        create_instrument_with_data()
    )

    response = client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": (
                account["id"]
            ),
            "symbol": symbol,
            "side": "buy",
            "order_type": "limit",
            "quantity": 1.0,
            "limit_price": 0.01,
            "time_in_force": "day",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    order = response.json()

    assert order["status"] in {
        "open",
        "accepted",
        "new",
        "pending",
    }

    cancel_response = client.post(
        (
            "/api/v1/paper/orders/"
            + order["id"]
            + "/cancel"
        )
    )

    assert (
        cancel_response.status_code
        == 200
    ), cancel_response.text

    cancelled = (
        cancel_response.json()
    )

    assert (
        cancelled["status"]
        == "cancelled"
    )


def test_filled_order_cannot_be_cancelled() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        create_instrument_with_data()
    )

    response = create_market_order(
        account_id=account["id"],
        symbol=symbol,
        quantity=1.0,
    )

    assert response.status_code == 201, (
        response.text
    )

    order = response.json()

    if order["status"] == "filled":
        cancel_response = client.post(
            (
                "/api/v1/paper/orders/"
                + order["id"]
                + "/cancel"
            )
        )

        assert (
            cancel_response.status_code
            in {
                400,
                409,
            }
        )

        return

    if order["status"] == "partially_filled":
        cancel_response = client.post(
            (
                "/api/v1/paper/orders/"
                + order["id"]
                + "/cancel"
            )
        )

        assert (
            cancel_response.status_code
            == 200
        ), cancel_response.text

        cancelled = (
            cancel_response.json()
        )

        assert (
            cancelled["status"]
            == "cancelled"
        )

        return

    assert order["status"] in {
        "accepted",
        "open",
        "pending",
    }