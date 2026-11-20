from __future__ import annotations

import numpy as np
import pandas as pd

from .core import Config


def folds(frame: pd.DataFrame, cfg: Config):
    dates = np.array(sorted(frame["timestamp"].unique()))
    cursor = cfg.train_periods + cfg.embargo_periods
    fold = 0
    while cursor + cfg.test_periods <= len(dates):
        test_dates = dates[cursor:cursor + cfg.test_periods]
        train_end = cursor - cfg.embargo_periods
        train_dates = dates[max(0, train_end - cfg.train_periods):train_end]
        if len(train_dates) >= cfg.min_train_periods:
            yield fold, frame[frame.timestamp.isin(train_dates)], frame[frame.timestamp.isin(test_dates)]
            fold += 1
        cursor += cfg.test_periods


def safe_rank_ic(section: pd.DataFrame, signal: str) -> float:
    pair = section[[signal, "forward_return"]].dropna()
    if len(pair) < 4 or pair[signal].nunique() < 2 or pair.forward_return.nunique() < 2:
        return np.nan
    return float(pair[signal].corr(pair.forward_return, method="spearman"))


def audit(frame: pd.DataFrame, features: list[str], cfg: Config) -> dict:
    counts = frame.groupby("timestamp")["symbol"].nunique()
    duplicate_count = int(frame.duplicated(["timestamp", "symbol"]).sum())
    future_named = [c for c in features if "future" in c.lower() or "forward" in c.lower()]
    return {
        "rows": len(frame), "periods": int(frame.timestamp.nunique()),
        "symbols": int(frame.symbol.nunique()), "minimum_symbols": int(counts.min()),
        "median_symbols": float(counts.median()), "duplicate_keys": duplicate_count,
        "features": features, "future_named_features": future_named,
        "checks": {
            "unique_keys": duplicate_count == 0,
            "sufficient_cross_section": int(counts.min()) >= cfg.min_symbols,
            "no_future_named_features": not future_named,
            "enough_periods": frame.timestamp.nunique() >= cfg.min_train_periods + cfg.test_periods + cfg.embargo_periods,
        },
    }

