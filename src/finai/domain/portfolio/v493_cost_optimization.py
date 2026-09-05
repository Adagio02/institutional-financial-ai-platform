from __future__ import annotations

from typing import Any

import pandas as pd

from finai.domain.portfolio.v49_construction import PortfolioConstructionEngine


def turnover_between(
    left: dict[str, float], right: dict[str, float]
) -> float:
    symbols = set(left) | set(right)
    return 0.5 * sum(abs(left.get(symbol, 0.0) - right.get(symbol, 0.0)) for symbol in symbols)


def optimize_rebalance(
    desired: dict[str, float],
    current: dict[str, float],
    *,
    engine: PortfolioConstructionEngine,
    maximum_turnover: float,
) -> tuple[dict[str, float], float, float]:
    """Find the largest feasible move toward desired weights within a turnover budget."""
    if maximum_turnover <= 0.0:
        raise ValueError("maximum_turnover must be positive.")
    full = engine.construct(desired).weights
    full_turnover = turnover_between(full, current)
    if not current or full_turnover <= maximum_turnover:
        return full, full_turnover, 1.0

    symbols = sorted(set(full) | set(current))
    low, high = 0.0, 1.0
    best = dict(current)
    best_turnover = 0.0
    for _ in range(40):
        fraction = (low + high) / 2.0
        proposal = {
            symbol: current.get(symbol, 0.0)
            + fraction * (full.get(symbol, 0.0) - current.get(symbol, 0.0))
            for symbol in symbols
        }
        proposal = {symbol: value for symbol, value in proposal.items() if abs(value) > 1e-12}
        candidate = engine.construct(proposal).weights
        turnover = turnover_between(candidate, current)
        if turnover <= maximum_turnover + 1e-10:
            low = fraction
            best = candidate
            best_turnover = turnover
        else:
            high = fraction
    return best, best_turnover, low


def optimize_portfolio_path(
    frame: pd.DataFrame,
    *,
    engine: PortfolioConstructionEngine,
    maximum_turnover: float = 0.20,
    one_way_cost_bps: float = 1.0,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    required = {"timestamp", "symbol", "weight", "realized_return"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("V4.9.3 portfolio frame missing: " + ", ".join(missing))
    if one_way_cost_bps < 0.0:
        raise ValueError("one_way_cost_bps cannot be negative.")

    current: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for timestamp, section in frame.groupby("timestamp", sort=True, observed=True):
        desired = dict(zip(section["symbol"].astype(str), section["weight"], strict=True))
        optimized, turnover, fraction = optimize_rebalance(
            desired,
            current,
            engine=engine,
            maximum_turnover=maximum_turnover,
        )
        realized_lookup = dict(
            zip(section["symbol"].astype(str), section["realized_return"], strict=True)
        )
        gross_return = sum(
            weight * float(realized_lookup.get(symbol, 0.0))
            for symbol, weight in optimized.items()
        )
        estimated_cost = turnover * float(one_way_cost_bps) / 10_000.0
        for symbol, weight in optimized.items():
            rows.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "desired_weight": float(desired.get(symbol, 0.0)),
                "weight": float(weight),
                "realized_return": float(realized_lookup.get(symbol, 0.0)),
            })
        diagnostics.append({
            "timestamp": timestamp,
            "turnover": float(turnover),
            "rebalance_fraction": float(fraction),
            "gross_exposure": float(sum(abs(value) for value in optimized.values())),
            "net_exposure": float(sum(optimized.values())),
            "gross_return": float(gross_return),
            "estimated_cost": float(estimated_cost),
            "net_return": float(gross_return - estimated_cost),
        })
        current = optimized
    if not rows:
        raise RuntimeError("V4.9.3 did not produce an optimized portfolio path.")
    return pd.DataFrame(rows), diagnostics
