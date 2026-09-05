from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


V481_TARGET_COLUMNS = [
    "target_market_neutral_return",
    "target_sector_neutral_return",
    "target_market_neutral_rank",
    "target_sector_neutral_rank",
]


def add_neutral_targets(frame: pd.DataFrame) -> pd.DataFrame:
    """Add future-return labels neutral to the timestamp market and sector means."""
    if frame.empty:
        raise ValueError("V4.8.1 feature panel is empty.")
    required = {"timestamp", "symbol", "sector", "future_return"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("V4.8.1 feature panel missing: " + ", ".join(missing))

    output = frame.copy()
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=True)
    output["future_return"] = pd.to_numeric(output["future_return"], errors="coerce")
    output.replace([np.inf, -np.inf], np.nan, inplace=True)

    market_mean = output.groupby("timestamp", observed=True)["future_return"].transform("mean")
    sector_mean = output.groupby(["timestamp", "sector"], observed=True)[
        "future_return"
    ].transform("mean")
    output["target_market_neutral_return"] = output["future_return"] - market_mean
    output["target_sector_neutral_return"] = output["future_return"] - sector_mean
    output["target_market_neutral_rank"] = output.groupby("timestamp", observed=True)[
        "target_market_neutral_return"
    ].rank(method="average", pct=True) - 0.5
    output["target_sector_neutral_rank"] = output.groupby(
        ["timestamp", "sector"], observed=True
    )["target_sector_neutral_return"].rank(method="average", pct=True) - 0.5
    return output


def target_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "symbols": int(frame["symbol"].nunique()),
        "timestamps": int(frame["timestamp"].nunique()),
        "target_columns": list(V481_TARGET_COLUMNS),
        "non_null_rows": {
            column: int(frame[column].notna().sum()) for column in V481_TARGET_COLUMNS
        },
        "mean_by_target": {
            column: float(frame[column].mean()) for column in V481_TARGET_COLUMNS
        },
    }
