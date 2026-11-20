from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .core import Config, config_dict, normalize, numeric_features, read_frame, sha256, write_frame, write_json
from .models import fit_predict_ranked
from .portfolio import metrics, simulate_ranked
from .validation import audit, folds, safe_rank_ic


def run_pipeline_v006(input_path: str, output_dir: str, cfg: Config) -> dict:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    frame = normalize(read_frame(input_path), cfg)
    candidates = numeric_features(frame)
    fold_list = list(folds(frame, cfg))
    if len(fold_list) < 2: raise RuntimeError("Fewer than two purged walk-forward folds")
    first_train = fold_list[0][1]
    features = [
        c for c in candidates
        if first_train[c].notna().mean() >= .60 and first_train[c].nunique(dropna=True) >= 10
    ]
    excluded = sorted(set(candidates) - set(features))
    if len(features) < 5: raise RuntimeError(f"Only {len(features)} adequately-covered features")
    audit_report = audit(frame, features, cfg)
    audit_report["excluded_low_coverage_features"] = excluded
    write_json(output / "audit.json", audit_report)
    predictions = []
    for fold_id, train, test in fold_list:
        part = fit_predict_ranked(train, test, features, cfg.seed + fold_id)
        part["fold"] = fold_id; predictions.append(part)
    pred = pd.concat(predictions, ignore_index=True)
    # Fold-local weights come only from each fold's training calibration tail.
    def combine(section: pd.DataFrame) -> pd.DataFrame:
        result = section.copy()
        ic = np.array([
            float(result.elastic_calibration_ic.iloc[0]),
            float(result.tree_calibration_ic.iloc[0]),
        ])
        weight = np.maximum(ic - cfg.ic_floor, 0.0)
        if weight.sum() == 0:
            result["ensemble"] = 0.0
        else:
            weight /= weight.sum()
            result["ensemble"] = result[["elastic", "tree"]].to_numpy() @ weight
        return result
    pred = pred.groupby("fold", group_keys=False, observed=True).apply(combine).reset_index(drop=True)
    pred_path = write_frame(pred, output / "oos_predictions.parquet")
    ledger, positions = simulate_ranked(pred, cfg)
    ledger.attrs["rebalance_every"] = cfg.rebalance_every
    ledger_path = write_frame(ledger, output / "ledger.parquet")
    positions_path = write_frame(positions, output / "positions.parquet")
    result_metrics = metrics(ledger)
    active_fraction = float((ledger.construction_status == "active").mean())
    mean_ensemble_ic = float(pred.groupby("timestamp", observed=True).apply(
        lambda section: safe_rank_ic(section, "ensemble"), include_groups=False
    ).dropna().mean())
    checks = {
        "minimum_periods": result_metrics["period_count"] >= 52,
        "active_fraction": active_fraction >= .80,
        "positive_rank_ic": mean_ensemble_ic > 0,
        "positive_net_return": result_metrics["cumulative_net_return"] > 0,
        "minimum_sharpe": result_metrics["annualized_sharpe"] >= .25,
        "maximum_drawdown": result_metrics["maximum_drawdown"] >= -.30,
        "turnover_limit": result_metrics["mean_turnover"] <= .50,
    }
    report = {
        "version": "5.6-research-006", "research_only": True,
        "eligible_to_create_new_locked_candidate": all(checks.values()),
        "not_eligible_for_champion": True, "config": config_dict(cfg),
        "features": features, "excluded_features": excluded,
        "mean_oos_rank_ic": mean_ensemble_ic, "active_fraction": active_fraction,
        "construction_status_counts": ledger.construction_status.value_counts().to_dict(),
        "metrics": result_metrics, "checks": checks,
        "artifacts": {"predictions": str(pred_path), "ledger": str(ledger_path), "positions": str(positions_path)},
        "hashes": {p.name: sha256(p) for p in (pred_path, ledger_path, positions_path)},
        "blocking_reasons": [k for k, v in checks.items() if not v],
    }
    write_json(output / "research_report.json", report)
    return report
