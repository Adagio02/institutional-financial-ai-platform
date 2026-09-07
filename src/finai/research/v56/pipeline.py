from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from .core import Config, config_dict, normalize, numeric_features, read_frame, sha256, write_frame, write_json
from .models import fit_predict
from .portfolio import metrics, simulate
from .validation import audit, folds, safe_rank_ic


def _ensemble_oos(pred: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    out = pred.sort_values(["timestamp", "symbol"]).copy()
    dates = sorted(out.timestamp.unique())
    history = {"elastic": [], "tree": []}
    pieces = []
    for date in dates:
        current = out[out.timestamp == date].copy()
        weights = []
        for model in history:
            trailing = pd.Series(history[model][-cfg.ic_lookback:]).dropna()
            estimate = float(trailing.mean()) if len(trailing) >= 20 else 0.0
            # Positive-only shrinkage: abstain from models without demonstrated past edge.
            weights.append(max(0.0, estimate - cfg.ic_floor))
        weights = np.asarray(weights)
        if weights.sum() == 0:
            current["ensemble"] = 0.0
        else:
            weights /= weights.sum()
            current["ensemble"] = current[["elastic", "tree"]].to_numpy() @ weights
        pieces.append(current)
        for model in history:
            history[model].append(safe_rank_ic(current, model))
    return pd.concat(pieces, ignore_index=True)


def run_pipeline(input_path: str, output_dir: str, cfg: Config | None = None, version: str = "5.6-research-003") -> dict:
    cfg = cfg or Config()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    raw = read_frame(input_path)
    frame = normalize(raw, cfg)
    features = numeric_features(frame)
    audit_report = audit(frame, features, cfg)
    write_json(output / "audit.json", audit_report)
    if not all(audit_report["checks"].values()):
        raise RuntimeError(f"Data audit failed: {audit_report['checks']}")
    predictions = []
    for fold_id, train, test in folds(frame, cfg):
        fold_pred = fit_predict(train, test, features, cfg.seed + fold_id)
        fold_pred["fold"] = fold_id
        predictions.append(fold_pred)
    if len(predictions) < 2:
        raise RuntimeError("Fewer than two purged walk-forward folds were produced")
    pred = pd.concat(predictions, ignore_index=True)
    pred = _ensemble_oos(pred, cfg)
    pred_path = write_frame(pred, output / "oos_predictions.parquet")
    ledger, positions = simulate(pred, cfg)
    ledger_path = write_frame(ledger, output / "ledger.parquet")
    positions_path = write_frame(positions, output / "positions.parquet")
    result_metrics = metrics(ledger)
    checks = {
        "minimum_periods": result_metrics["period_count"] >= max(52, 126 // cfg.rebalance_every),
        "positive_net_return": result_metrics["cumulative_net_return"] > 0,
        "minimum_sharpe": result_metrics["annualized_sharpe"] >= 0.25,
        "maximum_drawdown": result_metrics["maximum_drawdown"] >= -0.30,
        "turnover_limit": result_metrics["mean_turnover"] <= 0.50,
    }
    eligible = all(checks.values())
    report = {
        "version": version, "research_only": True,
        "eligible_to_create_new_locked_candidate": eligible,
        "not_eligible_for_champion": True,
        "config": config_dict(cfg), "audit": audit_report,
        "metrics": result_metrics, "checks": checks,
        "artifacts": {"predictions": str(pred_path), "ledger": str(ledger_path), "positions": str(positions_path)},
        "hashes": {p.name: sha256(p) for p in (pred_path, ledger_path, positions_path)},
        "blocking_reasons": [] if eligible else [name for name, passed in checks.items() if not passed],
    }
    write_json(output / "research_report.json", report)
    return report
