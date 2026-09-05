from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from finai.domain.learning.v473_cross_sectional import V473_FEATURE_COLUMNS


V48_RAW_FEATURE_COLUMNS = list(V473_FEATURE_COLUMNS)
V48_RANK_FEATURE_COLUMNS = [f"cs_rank_{column}" for column in V48_RAW_FEATURE_COLUMNS]
V48_ZSCORE_FEATURE_COLUMNS = [f"cs_zscore_{column}" for column in V48_RAW_FEATURE_COLUMNS]
V48_FEATURE_COLUMNS = (
    V48_RAW_FEATURE_COLUMNS + V48_RANK_FEATURE_COLUMNS + V48_ZSCORE_FEATURE_COLUMNS
)


def _robust_cross_sectional_zscore(values: pd.Series, *, clip: float) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    median = numeric.median()
    deviation = (numeric - median).abs().median()
    scale = 1.4826 * deviation
    if not np.isfinite(scale) or scale <= 1e-12:
        return pd.Series(0.0, index=values.index, dtype=float)
    return ((numeric - median) / scale).clip(-clip, clip)


def build_cross_sectional_feature_platform(
    frame: pd.DataFrame,
    *,
    minimum_cross_section_size: int = 10,
    zscore_clip: float = 5.0,
) -> pd.DataFrame:
    """Build timestamp-local ranks and robust z-scores without future leakage."""
    if frame.empty:
        raise ValueError("V4.8 source dataset is empty.")
    if minimum_cross_section_size < 3:
        raise ValueError("minimum_cross_section_size must be at least 3.")
    if zscore_clip <= 0.0:
        raise ValueError("zscore_clip must be positive.")

    required = {"timestamp", "symbol", *V48_RAW_FEATURE_COLUMNS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("V4.8 source dataset missing: " + ", ".join(missing))

    output = frame.copy()
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=True)
    output.replace([np.inf, -np.inf], np.nan, inplace=True)
    output = output.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
    output["cross_section_size"] = output.groupby("timestamp")["symbol"].transform("size")
    output = output.loc[output["cross_section_size"] >= minimum_cross_section_size].copy()

    grouped = output.groupby("timestamp", sort=False, observed=True)
    for column in V48_RAW_FEATURE_COLUMNS:
        output[f"cs_rank_{column}"] = grouped[column].rank(method="average", pct=True) - 0.5
        output[f"cs_zscore_{column}"] = grouped[column].transform(
            lambda values: _robust_cross_sectional_zscore(values, clip=zscore_clip)
        )

    output.replace([np.inf, -np.inf], np.nan, inplace=True)
    return output


def feature_platform_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "symbols": 0,
            "timestamps": 0,
            "feature_count": len(V48_FEATURE_COLUMNS),
            "complete_feature_rows": 0,
        }
    complete = frame[V48_FEATURE_COLUMNS].notna().all(axis=1)
    return {
        "rows": int(len(frame)),
        "symbols": int(frame["symbol"].nunique()),
        "timestamps": int(frame["timestamp"].nunique()),
        "first_timestamp": str(frame["timestamp"].min()),
        "last_timestamp": str(frame["timestamp"].max()),
        "feature_count": len(V48_FEATURE_COLUMNS),
        "complete_feature_rows": int(complete.sum()),
        "complete_feature_fraction": float(complete.mean()),
        "minimum_cross_section_size": int(frame["cross_section_size"].min()),
        "median_cross_section_size": float(frame.groupby("timestamp").size().median()),
    }
