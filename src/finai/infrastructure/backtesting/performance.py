import pandas as pd

from finai.domain.risk.metrics import (
    calculate_annualized_volatility,
    calculate_conditional_value_at_risk,
    calculate_downside_deviation,
    calculate_maximum_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_value_at_risk,
)


def calculate_equity_returns(
    equity_curve: pd.Series,
) -> pd.Series:
    return equity_curve.pct_change(fill_method=None)


def calculate_performance_metrics(
    equity_curve: pd.Series,
) -> dict[str, float | None]:
    if equity_curve.empty:
        raise ValueError("Equity curve cannot be empty.")

    initial_equity = float(equity_curve.iloc[0])

    final_equity = float(equity_curve.iloc[-1])

    total_return = (final_equity / initial_equity) - 1.0

    returns = calculate_equity_returns(equity_curve)

    return {
        "initial_equity": initial_equity,
        "final_equity": final_equity,
        "total_return": float(total_return),
        "maximum_drawdown": (calculate_maximum_drawdown(equity_curve)),
        "volatility": (calculate_annualized_volatility(returns)),
        "sharpe_ratio": (calculate_sharpe_ratio(returns)),
        "sortino_ratio": (calculate_sortino_ratio(returns)),
        "downside_deviation": (calculate_downside_deviation(returns)),
        "value_at_risk_95": (calculate_value_at_risk(returns)),
        "conditional_value_at_risk_95": (calculate_conditional_value_at_risk(returns)),
    }
