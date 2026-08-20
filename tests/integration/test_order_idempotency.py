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


def test_duplicate_client_order_id_returns_same_order() -> None:
    account_response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": (
                "Idempotency-"
                + uuid4().hex[:8]
            ),
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert account_response.status_code == 201, (
        account_response.text
    )

    account = account_response.json()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        f"ID{uuid4().hex[:6]}"
        .upper()
    )

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": (
                "Idempotency Instrument"
            ),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201, (
        instrument_response.text
    )

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

    assert ingestion_response.status_code == 201, (
        ingestion_response.text
    )

    client_order_id = (
        f"test-{uuid4()}"
    )

    payload = {
        "account_id": account["id"],
        "client_order_id": (
            client_order_id
        ),
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

    assert first_response.status_code == 201, (
        first_response.text
    )

    second_response = client.post(
        "/api/v1/paper/orders",
        json=payload,
    )

    assert second_response.status_code in {
        200,
        201,
    }, second_response.text

    first_order = first_response.json()

    second_order = second_response.json()

    assert (
        first_order["id"]
        == second_order["id"]
    )

    assert (
        first_order["client_order_id"]
        == client_order_id
    )