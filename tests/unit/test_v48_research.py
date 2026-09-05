from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from finai.domain.learning.v481_targets import add_neutral_targets
from finai.domain.learning.v482_ranking import walk_forward_predictions
from finai.domain.learning.v483_ic import signal_ic_series, summarize_ic
from finai.domain.learning.v48_features import (
    V48_FEATURE_COLUMNS,
    build_cross_sectional_feature_platform,
)
from finai.domain.learning.v473_cross_sectional import V473_FEATURE_COLUMNS


def _panel(periods: int = 100, symbols: int = 12) -> pd.DataFrame:
    rows = []
    names = [f"S{index:02d}" for index in range(symbols)]
    for time_index, timestamp in enumerate(
        pd.date_range("2025-01-01", periods=periods, freq="h", tz="UTC")
    ):
        for symbol_index, symbol in enumerate(names):
            row = {
                "timestamp": timestamp,
                "symbol": symbol,
                "sector": "A" if symbol_index < symbols // 2 else "B",
                "future_return": (symbol_index - symbols / 2) * 0.001,
            }
            for feature_index, column in enumerate(V473_FEATURE_COLUMNS):
                row[column] = float(symbol_index + feature_index + time_index * 0.001)
            rows.append(row)
    return pd.DataFrame(rows)


def test_v48_feature_platform_is_timestamp_local() -> None:
    result = build_cross_sectional_feature_platform(_panel())
    assert set(V48_FEATURE_COLUMNS).issubset(result.columns)
    assert result["cross_section_size"].min() == 12
    assert result.filter(like="cs_rank_").max().max() <= 0.5
    assert result.filter(like="cs_rank_").min().min() >= -0.5


def test_v481_targets_are_neutral_within_groups() -> None:
    result = add_neutral_targets(build_cross_sectional_feature_platform(_panel()))
    market_means = result.groupby("timestamp")["target_market_neutral_return"].mean()
    sector_means = result.groupby(["timestamp", "sector"])["target_sector_neutral_return"].mean()
    assert np.allclose(market_means, 0.0)
    assert np.allclose(sector_means, 0.0)


def test_v482_walk_forward_predictions_and_v483_ic() -> None:
    result = add_neutral_targets(build_cross_sectional_feature_platform(_panel()))
    prediction, reports = walk_forward_predictions(
        result,
        feature_columns=["cs_rank_return_1", "cs_zscore_return_1"],
        target_column="target_market_neutral_return",
        models={"ridge": Ridge(alpha=1.0)},
        fold_count=3,
        purge_timestamps=2,
        maximum_training_rows=10_000,
    )
    assert prediction["fold"].nunique() == 3
    assert len(reports) == 3
    series = signal_ic_series(
        prediction,
        prediction_column="prediction",
        target_column="target_market_neutral_return",
    )
    summary = summarize_ic(series)
    assert summary["timestamp_count"] > 0
    assert summary["mean_rank_ic"] > 0.9
