from __future__ import annotations

import numpy as np
import pandas as pd

from finai.domain.learning.v45_features import (
    V45_ENGINEERED_FEATURE_COLUMNS,
    apply_v45_features,
)


def test_v45_features_are_present() -> None:
    rows = 200
    timestamp = pd.date_range(
        "2026-01-05 14:30:00+00:00",
        periods=rows,
        freq="min",
    )
    base = np.linspace(
        100.0,
        102.0,
        rows,
    )
    frame = pd.DataFrame(
        {
            "timestamp": timestamp,
            "high_price": base + 0.1,
            "low_price": base - 0.1,
            "close_price": base,
            "volume": np.linspace(
                1000.0,
                2000.0,
                rows,
            ),
            "spy_close": base,
            "qqq_close": base,
            "return_1": pd.Series(base).pct_change(),
            "return_3": pd.Series(base).pct_change(3),
            "return_5": pd.Series(base).pct_change(5),
            "return_10": pd.Series(base).pct_change(10),
            "return_15": pd.Series(base).pct_change(15),
            "return_30": pd.Series(base).pct_change(30),
            "return_60": pd.Series(base).pct_change(60),
        }
    )

    # Minimal existing columns used by the engineered layer.
    frame["volatility_5"] = frame["return_1"].rolling(5).std()
    frame["volatility_20"] = frame["return_1"].rolling(20).std()
    frame["volatility_60"] = frame["return_1"].rolling(60).std()
    frame["range_pct"] = 0.002
    frame["ema_gap_10_30"] = frame["return_5"]
    frame["trend_strength"] = 1.0

    for horizon in (1, 5, 15, 30, 60):
        frame[f"spy_return_{horizon}"] = pd.Series(base).pct_change(horizon)
        frame[f"qqq_return_{horizon}"] = pd.Series(base).pct_change(horizon)

    frame["spy_volatility_20"] = frame["return_1"].rolling(20).std()
    frame["qqq_volatility_20"] = frame["return_1"].rolling(20).std()

    # Supply the rest of the inherited V421 feature schema with finite values.
    from finai.domain.learning.v421_features import V421_FEATURE_COLUMNS
    for column in V421_FEATURE_COLUMNS:
        if column not in frame:
            frame[column] = 0.1

    result = apply_v45_features(frame)

    assert len(result) > 0
    for column in V45_ENGINEERED_FEATURE_COLUMNS:
        assert column in result.columns
