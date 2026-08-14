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
            "name": ("Strategy Governance Account"),
            "initial_cash": 100_000.0,
            "base_currency": "USD",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_symbol() -> str:
    symbol = f"G{uuid4().hex[:7]}".upper()

    response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": ("Governance Test Instrument"),
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


def test_strategy_policy_can_disable_proposals() -> None:
    account = create_account()

    symbol = create_symbol()

    strategy_key = f"disabled-{uuid4().hex[:8]}"

    policy_response = client.put(
        (f"/api/v1/strategy/governance/policies/{account['id']}/{strategy_key}"),
        json={
            "enabled": False,
            "allow_buy": True,
            "allow_sell": True,
            "capital_budget_fraction": 0.25,
            "maximum_single_proposal_fraction": 0.25,
            "maximum_gross_exposure_fraction": 1.0,
            "maximum_symbol_fraction": 0.50,
            "maximum_daily_loss": 1000.0,
            "cooldown_seconds": 0,
            "maximum_active_proposals": 5,
        },
    )

    assert policy_response.status_code == 200, policy_response.text

    proposal_response = client.post(
        "/api/v1/strategy/proposals",
        json={
            "account_id": account["id"],
            "strategy_key": strategy_key,
            "symbol": symbol,
            "side": "buy",
            "confidence": 0.90,
        },
    )

    assert proposal_response.status_code == 201, proposal_response.text

    proposal = proposal_response.json()

    assert proposal["status"] == "rejected"

    assert "disabled" in (proposal["rejection_reason"] or "").lower()


def test_strategy_policy_endpoint() -> None:
    account = create_account()

    strategy_key = f"policy-{uuid4().hex[:8]}"

    response = client.get((f"/api/v1/strategy/governance/policies/{account['id']}/{strategy_key}"))

    assert response.status_code == 200, response.text

    policy = response.json()

    assert policy["account_id"] == account["id"]

    assert policy["strategy_key"] == strategy_key

    assert policy["enabled"] is True


def test_strategy_performance_endpoint() -> None:
    account = create_account()

    strategy_key = f"performance-{uuid4().hex[:8]}"

    response = client.get(
        (f"/api/v1/strategy/governance/performance/{account['id']}/{strategy_key}")
    )

    assert response.status_code == 200, response.text

    result = response.json()

    assert result["daily_net_pnl"] == 0

    assert result["gross_book_exposure"] == 0

    assert result["position_count"] == 0
