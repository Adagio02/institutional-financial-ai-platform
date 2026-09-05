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


def create_account() -> dict:
    response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": (
                "Strategy-"
                + uuid4().hex[:8]
            ),
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def create_instrument_with_data() -> str:
    symbol = (
        f"S{uuid4().hex[:7]}"
        .upper()
    )

    response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": (
                "Strategy Test Instrument"
            ),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert response.status_code == 201, (
        response.text
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

    return symbol


def test_create_approve_and_execute_proposal() -> None:
    account = create_account()

    ensure_trading_enabled(
        account["id"]
    )

    symbol = (
        create_instrument_with_data()
    )

    create_response = client.post(
        "/api/v1/strategy/proposals",
        json={
            "account_id": (
                account["id"]
            ),
            "symbol": symbol,
            "side": "buy",
            "confidence": 0.85,
        },
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    proposal = create_response.json()

    assert (
        proposal["status"]
        == "pending_approval"
    )

    assert (
        proposal["quantity"]
        > 0
    )

    assert (
        proposal["proposed_notional"]
        > 0
    )

    assert (
        proposal["reference_price"]
        > 0
    )

    proposal_id = proposal["id"]

    premature_response = client.post(
        (
            "/api/v1/strategy/proposals/"
            f"{proposal_id}/execute"
        )
    )

    assert premature_response.status_code == 409, (
        premature_response.text
    )

    approval_response = client.post(
        (
            "/api/v1/strategy/proposals/"
            f"{proposal_id}/approve"
        ),
        json={
            "reason": (
                "Integration test approval"
            )
        },
    )

    assert approval_response.status_code == 200, (
        approval_response.text
    )

    approved = approval_response.json()

    assert (
        approved["status"]
        == "approved"
    )

    assert (
        approved["approved_at"]
        is not None
    )

    execution_response = client.post(
        (
            "/api/v1/strategy/proposals/"
            f"{proposal_id}/execute"
        )
    )

    assert execution_response.status_code == 200, (
        execution_response.text
    )

    executed = execution_response.json()

    assert executed["status"] in {
        "executed",
        "execution_rejected",
    }

    assert (
        executed["order_id"]
        is not None
    )

    if (
        executed["status"]
        == "executed"
    ):
        order_response = client.get(
            (
                "/api/v1/paper/orders/"
                f"{executed['order_id']}"
            )
        )

        assert order_response.status_code == 200, (
            order_response.text
        )

        order = order_response.json()

        assert (
            order["symbol"]
            == symbol
        )

        assert (
            order["client_order_id"]
            == f"proposal-{proposal_id}"
        )

        assert order["status"] in {
            "partially_filled",
            "filled",
        }


def test_low_confidence_proposal_is_rejected() -> None:
    account = create_account()

    symbol = (
        create_instrument_with_data()
    )

    response = client.post(
        "/api/v1/strategy/proposals",
        json={
            "account_id": (
                account["id"]
            ),
            "symbol": symbol,
            "side": "buy",
            "confidence": 0.25,
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    proposal = response.json()

    assert (
        proposal["status"]
        == "rejected"
    )

    assert (
        proposal["quantity"]
        == 0
    )

    assert (
        proposal["rejection_reason"]
        is not None
    )


def test_sell_proposal_without_position_is_rejected() -> None:
    account = create_account()

    symbol = (
        create_instrument_with_data()
    )

    response = client.post(
        "/api/v1/strategy/proposals",
        json={
            "account_id": (
                account["id"]
            ),
            "symbol": symbol,
            "side": "sell",
            "confidence": 0.90,
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    proposal = response.json()

    assert (
        proposal["status"]
        == "rejected"
    )

    assert (
        "existing long position"
        in proposal["rejection_reason"]
    )


def test_pending_proposal_can_be_manually_rejected() -> None:
    account = create_account()

    symbol = (
        create_instrument_with_data()
    )

    create_response = client.post(
        "/api/v1/strategy/proposals",
        json={
            "account_id": (
                account["id"]
            ),
            "symbol": symbol,
            "side": "buy",
            "confidence": 0.90,
        },
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    proposal = create_response.json()

    assert (
        proposal["status"]
        == "pending_approval"
    )

    reject_response = client.post(
        (
            "/api/v1/strategy/proposals/"
            f"{proposal['id']}/reject"
        ),
        json={
            "reason": (
                "Manual integration test rejection"
            )
        },
    )

    assert reject_response.status_code == 200, (
        reject_response.text
    )

    rejected = reject_response.json()

    assert (
        rejected["status"]
        == "rejected"
    )

    assert (
        rejected["rejected_at"]
        is not None
    )