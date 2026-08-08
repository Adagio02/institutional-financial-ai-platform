from fastapi.testclient import TestClient

from finai.api.main import application
from tests.integration.test_prediction import (
    create_model_and_dataset,
)


client = TestClient(application)


def test_create_backtest() -> None:
    model_id, dataset_id, symbol = (
        create_model_and_dataset()
    )

    response = client.post(
        "/api/v1/backtests",
        json={
            "model_id": model_id,
            "dataset_id": dataset_id,
            "symbol": symbol,
            "initial_capital": 100_000.0,
            "long_threshold": 0.60,
            "short_threshold": 0.40,
            "position_size_fraction": 0.10,
            "commission_bps": 1.0,
            "slippage_bps": 2.0,
            "allow_short": False,
        },
    )

    assert response.status_code == 201

    backtest = response.json()

    assert backtest["status"] == "completed"
    assert (
        backtest["initial_capital"]
        == 100_000.0
    )
    assert backtest["final_equity"] is not None
    assert backtest["metrics"]

    run_id = backtest["id"]

    get_response = client.get(
        f"/api/v1/backtests/{run_id}"
    )

    assert get_response.status_code == 200

    equity_response = client.get(
        f"/api/v1/backtests/{run_id}/equity"
    )

    assert equity_response.status_code == 200
    assert len(
        equity_response.json()
    ) > 0


def test_backtest_risk_metrics() -> None:
    model_id, dataset_id, symbol = (
        create_model_and_dataset()
    )

    backtest_response = client.post(
        "/api/v1/backtests",
        json={
            "model_id": model_id,
            "dataset_id": dataset_id,
            "symbol": symbol,
            "initial_capital": 100_000.0,
            "long_threshold": 0.60,
            "short_threshold": 0.40,
            "position_size_fraction": 0.10,
            "commission_bps": 1.0,
            "slippage_bps": 2.0,
            "allow_short": False,
        },
    )

    assert (
        backtest_response.status_code
        == 201
    )

    run_id = backtest_response.json()[
        "id"
    ]

    risk_response = client.get(
        f"/api/v1/risk/backtests/{run_id}"
    )

    assert risk_response.status_code == 200

    risk = risk_response.json()

    assert "maximum_drawdown" in risk
    assert "sharpe_ratio" in risk
    assert "sortino_ratio" in risk
    assert "value_at_risk_95" in risk