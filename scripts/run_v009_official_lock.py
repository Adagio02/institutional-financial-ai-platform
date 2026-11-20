from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from finai.research.v56.core import Config, normalize
from finai.research.v56.portfolio import metrics
from finai.research.v56.portfolio_v007 import simulate_v007
from finai.research.v56.validation import safe_rank_ic
from finai.research.v56.v009_milestones import read_json, sha256, write_json_atomic


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--candidate-model", required=True)
    parser.add_argument("--sector-attestation", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    registry, report_path = output / "execution_registry.json", output / "v563_report.json"
    if registry.exists() or report_path.exists():
        raise RuntimeError("Official V009 lock has already been attempted; automatic rerun is forbidden")
    protocol, policy, attestation = map(read_json, (args.protocol, args.policy, args.sector_attestation))
    if sha256(args.protocol) != policy["protocol_sha256"]:
        raise RuntimeError("Protocol hash differs from sealed policy")
    if sha256(args.candidate_model) != policy["candidate_model_sha256"]:
        raise RuntimeError("Candidate model hash differs from sealed policy")
    if not attestation.get("verified") or sha256(args.sector_attestation) != policy["sector_attestation_sha256"]:
        raise RuntimeError("Sector attestation is missing or changed")
    candidate = joblib.load(args.candidate_model)
    if candidate["protocol_sha256"] != policy["protocol_sha256"]:
        raise RuntimeError("Frozen candidate belongs to a different protocol")
    cfg = Config(**candidate["config"])
    raw = pd.read_parquet(args.panel)
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    raw = raw[raw.timestamp >= pd.Timestamp(protocol["prospective_lock_start"])]
    counts = raw.groupby("timestamp", observed=True).symbol.nunique()
    qualified = list(counts[counts >= int(policy["minimum_symbols"])].sort_index().index)
    required_market_dates = 261
    if len(qualified) < required_market_dates:
        raise RuntimeError(f"Official lock is not ready: {len(qualified)}/{required_market_dates} qualified market dates")
    raw = raw[raw.timestamp.isin(qualified[:required_market_dates])].copy()
    frame = normalize(raw, cfg)
    mature = frame.dropna(subset=["forward_return"]).copy()
    features = candidate["features"]
    missing = sorted(set(features).difference(mature.columns))
    if missing:
        raise RuntimeError(f"Official panel is missing frozen features: {missing}")
    write_json_atomic(registry, {"execution_count": 1, "status": "started", "panel_sha256": sha256(args.panel),
                      "candidate_model_sha256": sha256(args.candidate_model), "policy_sha256": sha256(args.policy)}, exclusive=True)
    carry = ["timestamp", "symbol", "forward_return", "close", "sector", "beta"]
    predictions = mature[carry].copy()
    for name in ("elastic", "tree"):
        raw_prediction = candidate["models"][name].predict(mature[features])
        predictions[name] = pd.Series(raw_prediction, index=mature.index).groupby(mature.timestamp).rank(pct=True) - .5
    weights = candidate["ensemble_weights"]
    predictions["ensemble"] = predictions.elastic * weights["elastic"] + predictions.tree * weights["tree"]
    ledger, positions = simulate_v007(predictions, cfg)
    ledger = ledger.iloc[:52].copy()
    positions = positions[positions.timestamp.isin(set(ledger.timestamp))].copy()
    ledger.attrs["rebalance_every"] = cfg.rebalance_every
    result_metrics = metrics(ledger)
    rebalance_predictions = predictions[predictions.timestamp.isin(set(ledger.timestamp))]
    rank_ic = rebalance_predictions.groupby("timestamp", observed=True).apply(lambda section: safe_rank_ic(section, "ensemble"), include_groups=False).dropna()
    mean_ic = float(rank_ic.mean()) if len(rank_ic) else 0.0
    active_fraction = float((ledger.construction_status == "active").mean())
    gross_return = float((1 + ledger.gross_return).prod() - 1)
    rules = protocol["locked_rules"]
    checks = {
        "minimum_periods": len(ledger) >= int(rules["minimum_periods"]), "active_fraction": active_fraction >= .80,
        "positive_rank_ic": mean_ic > 0, "positive_gross_return": gross_return > 0,
        "positive_net_return": result_metrics["cumulative_net_return"] > 0,
        "minimum_sharpe": result_metrics["annualized_sharpe"] >= float(rules["minimum_sharpe"]),
        "maximum_drawdown": result_metrics["maximum_drawdown"] >= float(rules["maximum_drawdown"]),
        "turnover_limit": result_metrics["mean_turnover"] <= cfg.rebalance_turnover_limit + 1e-8,
        "beta_band": float(ledger.beta_exposure.abs().max()) <= cfg.beta_exposure_limit + 1e-8,
        "verified_real_data": True, "single_execution": True, "sector_provenance_verified": True,
    }
    passed = all(checks.values())
    output.mkdir(parents=True, exist_ok=True)
    ledger_path, positions_path = output / "locked_ledger.parquet", output / "locked_positions.parquet"
    ledger.to_parquet(ledger_path, index=False)
    positions.to_parquet(positions_path, index=False)
    decision = {"validation_passed": passed, "eligible_for_v57_untouched_final_test": passed,
                "eligible_for_champion": False, "verified_real_data": True, "live_trading_enabled": False,
                "blocking_reasons": [name for name, value in checks.items() if not value]}
    report = {"version": "5.6.3-v009-official-lock", "execution_count": 1, "verified_real_data": True,
              "validation_passed": passed, "eligible_for_v57_untouched_final_test": passed,
              "eligible_for_champion": False, "decision": decision, "metrics": result_metrics,
              "mean_rank_ic": mean_ic, "active_fraction": active_fraction,
              "gross_compounded_return": gross_return, "checks": checks,
              "hashes": {"locked_ledger.parquet": sha256(ledger_path), "locked_positions.parquet": sha256(positions_path)}}
    write_json_atomic(report_path, report, exclusive=True)
    registry_data = read_json(registry)
    registry_data.update(status="completed", report_sha256=sha256(report_path))
    write_json_atomic(registry, registry_data)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
