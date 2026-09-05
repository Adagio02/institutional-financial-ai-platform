from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"timestamp", "symbol", "alpha__ensemble", "forward_return"}


def normalize_ensemble(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError("V5.5 ensemble input missing: " + ", ".join(missing))
    output = frame[list(sorted(REQUIRED_COLUMNS))].copy()
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=True, errors="coerce")
    output["symbol"] = output["symbol"].astype(str).str.upper().str.strip()
    output["alpha__ensemble"] = pd.to_numeric(output["alpha__ensemble"], errors="coerce")
    output["forward_return"] = pd.to_numeric(output["forward_return"], errors="coerce")
    output = output.dropna().drop_duplicates(["timestamp", "symbol"], keep="last")
    output = output.loc[output["symbol"].ne("")].sort_values(["timestamp", "symbol"])
    if output.empty:
        raise RuntimeError("V5.5 rejected every ensemble observation.")
    return output.reset_index(drop=True)


def build_purged_folds(
    frame: pd.DataFrame,
    *,
    minimum_training_periods: int = 5,
    test_periods: int = 2,
    embargo_periods: int = 1,
) -> list[dict[str, Any]]:
    dates = list(frame["timestamp"].drop_duplicates().sort_values())
    first_test = minimum_training_periods + embargo_periods
    folds: list[dict[str, Any]] = []
    fold_id = 1
    for test_start in range(first_test, len(dates) - 1, test_periods):
        test_end = min(test_start + test_periods, len(dates) - 1)
        training_end = test_start - embargo_periods
        train = dates[:training_end]
        test = dates[test_start:test_end]
        if len(train) < minimum_training_periods or not test:
            continue
        folds.append({
            "fold_id": fold_id,
            "train_start": train[0].isoformat(), "train_end": train[-1].isoformat(),
            "test_start": test[0].isoformat(), "test_end": test[-1].isoformat(),
            "training_period_count": len(train), "test_period_count": len(test),
            "embargo_period_count": embargo_periods,
        })
        fold_id += 1
    if not folds:
        raise RuntimeError(
            "V5.5 needs more synchronized periods for purged walk-forward folds. "
            f"Received {len(dates)} periods."
        )
    return folds


def fold_manifest(folds: list[dict[str, Any]], source_rows: int) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0", "source_rows": int(source_rows),
        "fold_count": len(folds), "folds": folds,
        "policy": "expanding_train_purged_embargo_non_overlapping_test",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def _target_weights(section: pd.DataFrame, long_fraction: float) -> pd.Series:
    if len(section) < 4:
        return pd.Series(0.0, index=section.index)
    percentile = section["alpha__ensemble"].rank(pct=True, method="first")
    long_mask = percentile >= 1.0 - long_fraction
    short_mask = percentile <= long_fraction
    weights = pd.Series(0.0, index=section.index)
    if long_mask.any():
        weights.loc[long_mask] = 0.5 / int(long_mask.sum())
    if short_mask.any():
        weights.loc[short_mask] = -0.5 / int(short_mask.sum())
    return weights


def simulate_walk_forward(
    frame: pd.DataFrame,
    folds: list[dict[str, Any]],
    *,
    long_fraction: float = 0.20,
    transaction_cost_bps: float = 5.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < long_fraction <= 0.5:
        raise ValueError("long_fraction must be in (0, 0.5].")
    rows: list[dict[str, Any]] = []
    positions: list[pd.DataFrame] = []
    prior_weights: dict[str, float] = {}
    for fold in folds:
        start, end = pd.Timestamp(fold["test_start"]), pd.Timestamp(fold["test_end"])
        test = frame.loc[frame["timestamp"].between(start, end)].copy()
        for timestamp, section in test.groupby("timestamp", sort=True, observed=True):
            section = section.copy()
            section["weight"] = _target_weights(section, long_fraction)
            new_weights = dict(zip(section["symbol"], section["weight"]))
            names = set(prior_weights).union(new_weights)
            turnover = 0.5 * sum(abs(new_weights.get(name, 0.0) - prior_weights.get(name, 0.0)) for name in names)
            gross_return = float((section["weight"] * section["forward_return"]).sum())
            cost = float(turnover * transaction_cost_bps / 10_000.0)
            rows.append({
                "fold_id": fold["fold_id"], "timestamp": timestamp,
                "gross_return": gross_return, "turnover": turnover,
                "transaction_cost": cost, "net_return": gross_return - cost,
                "gross_exposure": float(section["weight"].abs().sum()),
                "net_exposure": float(section["weight"].sum()),
            })
            section["fold_id"] = fold["fold_id"]
            positions.append(section[["fold_id", "timestamp", "symbol", "alpha__ensemble", "forward_return", "weight"]])
            prior_weights = new_weights
    returns = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    if returns.empty:
        raise RuntimeError("V5.5 walk-forward simulation produced no test returns.")
    return returns, pd.concat(positions, ignore_index=True)


def _max_drawdown(returns: pd.Series) -> float:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    return float((equity / equity.cummax() - 1.0).min())


def qualify_walk_forward(returns: pd.DataFrame) -> dict[str, Any]:
    net = returns["net_return"]
    mean = float(net.mean())
    volatility = float(net.std(ddof=0))
    fold_metrics = []
    for fold_id, section in returns.groupby("fold_id", observed=True):
        fold_metrics.append({
            "fold_id": int(fold_id), "period_count": int(len(section)),
            "net_return": float((1 + section["net_return"]).prod() - 1),
            "positive_period_fraction": float((section["net_return"] > 0).mean()),
        })
    positive_folds = sum(item["net_return"] > 0 for item in fold_metrics)
    annualized_sharpe = float(mean / volatility * np.sqrt(252)) if volatility > 0 else 0.0
    result = {
        "period_count": int(len(returns)), "fold_count": len(fold_metrics),
        "fold_metrics": fold_metrics, "positive_fold_count": positive_folds,
        "cumulative_net_return": float((1 + net).prod() - 1),
        "annualized_sharpe": annualized_sharpe,
        "maximum_drawdown": _max_drawdown(net),
        "positive_period_fraction": float((net > 0).mean()),
        "mean_turnover": float(returns["turnover"].mean()),
        "total_transaction_cost": float(returns["transaction_cost"].sum()),
    }
    result["eligible_for_v56_locked_validation"] = bool(
        len(fold_metrics) >= 2
        and positive_folds >= max(1, int(np.ceil(len(fold_metrics) / 2)))
        and result["cumulative_net_return"] > 0
        and np.isfinite(annualized_sharpe)
    )
    return result

