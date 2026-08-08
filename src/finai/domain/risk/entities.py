from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    volatility: float | None
    downside_deviation: float | None
    maximum_drawdown: float
    value_at_risk_95: float | None
    conditional_value_at_risk_95: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
