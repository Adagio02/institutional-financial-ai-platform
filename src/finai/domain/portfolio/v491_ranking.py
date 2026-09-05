from __future__ import annotations

import math
from typing import Any

import pandas as pd

from finai.domain.portfolio.v49_construction import PortfolioConstructionEngine


def build_long_short_ranking_portfolios(
    predictions: pd.DataFrame,
    *,
    model_name: str,
    target_column: str,
    engine: PortfolioConstructionEngine,
    quantile_fraction: float = 0.20,
    minimum_positions_per_side: int = 5,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Convert out-of-sample scores into timestamp-local long/short weights."""
    if not 0.0 < quantile_fraction <= 0.5:
        raise ValueError("quantile_fraction must be in (0, 0.5].")
    if minimum_positions_per_side < 1:
        raise ValueError("minimum_positions_per_side must be positive.")
    required = {
        "timestamp",
        "symbol",
        "model_name",
        "target_column",
        "prediction",
        target_column,
    }
    missing = sorted(required.difference(predictions.columns))
    if missing:
        raise ValueError("V4.9.1 predictions missing: " + ", ".join(missing))

    selected = predictions.loc[
        (predictions["model_name"] == model_name)
        & (predictions["target_column"] == target_column)
    ].copy()
    if selected.empty:
        raise ValueError("V4.9.1 could not find the V4.8.3 research leader predictions.")

    long_target = (
        engine.constraints.target_gross_exposure
        + engine.constraints.target_net_exposure
    ) / 2.0
    short_target = (
        engine.constraints.target_gross_exposure
        - engine.constraints.target_net_exposure
    ) / 2.0
    cap = engine.constraints.maximum_absolute_weight
    minimum_for_cap = max(
        math.ceil(long_target / cap) if long_target > 0.0 else 0,
        math.ceil(short_target / cap) if short_target > 0.0 else 0,
    )

    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for timestamp, section in selected.groupby("timestamp", sort=True, observed=True):
        usable = section.dropna(subset=["prediction", target_column]).copy()
        usable = usable.sort_values(["prediction", "symbol"], kind="mergesort")
        side_count = max(
            minimum_positions_per_side,
            minimum_for_cap,
            int(math.floor(len(usable) * quantile_fraction)),
        )
        if len(usable) < side_count * 2:
            continue
        short = usable.head(side_count)
        long = usable.tail(side_count)
        proposed = {
            str(row.symbol): -(side_count - index)
            for index, row in enumerate(short.itertuples(index=False))
        }
        proposed.update({
            str(row.symbol): index + 1
            for index, row in enumerate(long.itertuples(index=False))
        })
        result = engine.construct(proposed)
        lookup = usable.set_index("symbol")
        portfolio_return = 0.0
        for symbol, weight in result.weights.items():
            source = lookup.loc[symbol]
            realized = float(source[target_column])
            portfolio_return += weight * realized
            rows.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "weight": weight,
                "prediction": float(source["prediction"]),
                "realized_return": realized,
                "model_name": model_name,
                "target_column": target_column,
            })
        diagnostics.append({
            "timestamp": timestamp,
            "universe_size": int(len(usable)),
            "positions_per_side": side_count,
            "position_count": result.position_count,
            "gross_exposure": result.gross_exposure,
            "net_exposure": result.net_exposure,
            "portfolio_return": float(portfolio_return),
        })
    if not rows:
        raise RuntimeError("V4.9.1 did not produce any ranking portfolios.")
    return pd.DataFrame(rows), diagnostics
