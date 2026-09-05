import math

import numpy as np
import pandas as pd


def calculate_maximum_drawdown(
    equity_curve: pd.Series,
) -> float:
    if equity_curve.empty:
        return 0.0

    running_maximum = equity_curve.cummax()

    drawdown = (equity_curve / running_maximum) - 1.0

    return float(drawdown.min())


def calculate_annualized_volatility(
    returns: pd.Series,
    *,
    periods_per_year: int = 252,
) -> float | None:
    clean = returns.dropna()

    if len(clean) < 2:
        return None

    return float(clean.std(ddof=1) * math.sqrt(periods_per_year))


def calculate_sharpe_ratio(
    returns: pd.Series,
    *,
    annual_risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float | None:
    clean = returns.dropna()

    if len(clean) < 2:
        return None

    periodic_risk_free_rate = annual_risk_free_rate / periods_per_year

    excess_returns = clean - periodic_risk_free_rate

    standard_deviation = excess_returns.std(ddof=1)

    if standard_deviation == 0:
        return None

    return float(excess_returns.mean() / standard_deviation * math.sqrt(periods_per_year))


def calculate_downside_deviation(
    returns: pd.Series,
    *,
    periods_per_year: int = 252,
) -> float | None:
    downside = returns[returns < 0].dropna()

    if len(downside) < 2:
        return None

    return float(downside.std(ddof=1) * math.sqrt(periods_per_year))


def calculate_sortino_ratio(
    returns: pd.Series,
    *,
    annual_risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float | None:
    clean = returns.dropna()

    if len(clean) < 2:
        return None

    downside_deviation = calculate_downside_deviation(
        clean,
        periods_per_year=periods_per_year,
    )

    if downside_deviation is None or downside_deviation == 0:
        return None

    annualized_return = clean.mean() * periods_per_year

    return float((annualized_return - annual_risk_free_rate) / downside_deviation)


def calculate_value_at_risk(
    returns: pd.Series,
    *,
    confidence: float = 0.95,
) -> float | None:
    clean = returns.dropna()

    if clean.empty:
        return None

    percentile = (1.0 - confidence) * 100.0

    return float(
        np.percentile(
            clean,
            percentile,
        )
    )


def calculate_conditional_value_at_risk(
    returns: pd.Series,
    *,
    confidence: float = 0.95,
) -> float | None:
    clean = returns.dropna()

    if clean.empty:
        return None

    value_at_risk = calculate_value_at_risk(
        clean,
        confidence=confidence,
    )

    if value_at_risk is None:
        return None

    tail = clean[clean <= value_at_risk]

    if tail.empty:
        return value_at_risk

    return float(tail.mean())
