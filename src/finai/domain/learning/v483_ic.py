from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _safe_correlation(left: pd.Series, right: pd.Series, *, method: str) -> float:
    pair = pd.concat([left, right], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(pair) < 3 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return float("nan")
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method=method))


def signal_ic_series(
    frame: pd.DataFrame,
    *,
    prediction_column: str,
    target_column: str,
    minimum_cross_section_size: int = 10,
) -> pd.DataFrame:
    required = {"timestamp", prediction_column, target_column}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("V4.8.3 prediction frame missing: " + ", ".join(missing))

    rows: list[dict[str, Any]] = []
    for timestamp, section in frame.groupby("timestamp", sort=True, observed=True):
        usable = section[[prediction_column, target_column]].dropna()
        if len(usable) < minimum_cross_section_size:
            continue
        rows.append({
            "timestamp": timestamp,
            "cross_section_size": int(len(usable)),
            "ic": _safe_correlation(
                usable[prediction_column], usable[target_column], method="pearson"
            ),
            "rank_ic": _safe_correlation(
                usable[prediction_column], usable[target_column], method="spearman"
            ),
        })
    return pd.DataFrame(rows)


def summarize_ic(series: pd.DataFrame) -> dict[str, Any]:
    if series.empty:
        return {
            "timestamp_count": 0,
            "mean_ic": 0.0,
            "mean_rank_ic": 0.0,
            "rank_ic_information_ratio": 0.0,
            "positive_rank_ic_fraction": 0.0,
        }
    ic = series["ic"].dropna().to_numpy(dtype=float)
    rank_ic = series["rank_ic"].dropna().to_numpy(dtype=float)
    rank_mean = float(rank_ic.mean()) if len(rank_ic) else 0.0
    rank_std = float(rank_ic.std(ddof=1)) if len(rank_ic) > 1 else 0.0
    return {
        "timestamp_count": int(len(series)),
        "mean_ic": float(ic.mean()) if len(ic) else 0.0,
        "median_ic": float(np.median(ic)) if len(ic) else 0.0,
        "mean_rank_ic": rank_mean,
        "median_rank_ic": float(np.median(rank_ic)) if len(rank_ic) else 0.0,
        "rank_ic_std": rank_std,
        "rank_ic_information_ratio": rank_mean / rank_std if rank_std > 0.0 else 0.0,
        "positive_rank_ic_fraction": float(np.mean(rank_ic > 0.0)) if len(rank_ic) else 0.0,
        "worst_rank_ic": float(rank_ic.min()) if len(rank_ic) else 0.0,
        "best_rank_ic": float(rank_ic.max()) if len(rank_ic) else 0.0,
    }
