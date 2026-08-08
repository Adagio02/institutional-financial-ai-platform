from uuid import UUID

from pydantic import BaseModel


class BacktestRiskResponse(BaseModel):
    backtest_run_id: UUID

    initial_equity: float
    final_equity: float
    total_return: float

    maximum_drawdown: float

    volatility: float | None
    downside_deviation: float | None

    sharpe_ratio: float | None
    sortino_ratio: float | None

    value_at_risk_95: float | None

    conditional_value_at_risk_95: float | None
