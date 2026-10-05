from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .core import Config, config_dict, read_frame, sha256, write_frame, write_json
from .portfolio import metrics
from .portfolio_v007 import simulate_v007
from .validation import safe_rank_ic


def run_v007(prediction_path: str, output_dir: str, cfg: Config) -> dict:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    predictions = read_frame(prediction_path)
    required = {"timestamp","symbol","forward_return","ensemble","sector","beta"}
    missing = required.difference(predictions.columns)
    if missing: raise ValueError(f"Predictions missing columns: {sorted(missing)}")
    predictions["timestamp"] = pd.to_datetime(predictions.timestamp, utc=True)
    ledger, positions = simulate_v007(predictions, cfg)
    ledger_path = write_frame(ledger, output / "ledger.parquet")
    positions_path = write_frame(positions, output / "positions.parquet")
    result_metrics = metrics(ledger, cfg.rebalance_every)
    rebalance = predictions[predictions.timestamp.isin(ledger.timestamp)]
    daily_ic = rebalance.groupby("timestamp", observed=True).apply(
        lambda section: safe_rank_ic(section, "ensemble"), include_groups=False
    ).dropna()
    mean_ic = float(daily_ic.mean()) if len(daily_ic) else 0.0
    active_fraction = float((ledger.construction_status == "active").mean())
    checks = {
        "minimum_periods": len(ledger) >= 52,
        "active_fraction": active_fraction >= .80,
        "positive_rank_ic": mean_ic > 0,
        "positive_gross_return": float((1 + ledger.gross_return).prod() - 1) > 0,
        "positive_net_return": result_metrics["cumulative_net_return"] > 0,
        "minimum_sharpe": result_metrics["annualized_sharpe"] >= .25,
        "maximum_drawdown": result_metrics["maximum_drawdown"] >= -.30,
        "turnover_limit": result_metrics["mean_turnover"] <= cfg.rebalance_turnover_limit + 1e-8,
        "beta_band": float(ledger.beta_exposure.abs().max()) <= cfg.beta_exposure_limit + 1e-8,
    }
    passed = all(checks.values())
    report = {
        "version":"5.6-research-007","research_only":True,
        "development_window_previously_observed":True,
        "eligible_to_freeze_candidate":passed,
        "eligible_to_create_new_locked_candidate":passed,
        "not_eligible_for_v57_without_new_lock":True,
        "config":config_dict(cfg),"mean_rebalance_rank_ic":mean_ic,
        "active_fraction":active_fraction,
        "gross_compounded_return":float((1 + ledger.gross_return).prod() - 1),
        "construction_status_counts":ledger.construction_status.value_counts().to_dict(),
        "metrics":result_metrics,"checks":checks,
        "artifacts":{"ledger":str(ledger_path),"positions":str(positions_path)},
        "hashes":{p.name:sha256(p) for p in (ledger_path,positions_path)},
        "blocking_reasons":[k for k,v in checks.items() if not v],
        "required_next_step":"Freeze policy and evaluate once on genuinely unseen V5.6 locked data; do not use this development result as V5.7 authorization.",
    }
    write_json(output / "research_report.json", report)
    return report
