from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from finai.research.v56.core import Config, normalize
from finai.research.v56.models import _elastic, _tree
from finai.research.v56.validation import safe_rank_ic
from finai.research.v56.v009_milestones import read_json, sha256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--model-audit", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--universe", required=True)
    parser.add_argument("--sector-attestation", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"Frozen candidate already exists: {output}")
    protocol = read_json(args.protocol)
    attestation = read_json(args.sector_attestation)
    universe_hash = sha256(args.universe)
    if protocol.get("universe_sha256") != universe_hash:
        raise RuntimeError("Protocol and universe hashes differ")
    if not attestation.get("verified") or attestation.get("universe_sha256") != universe_hash:
        raise RuntimeError("A matching verified sector attestation is required")
    cfg = Config(horizon=5, rebalance_every=5, min_symbols=int(protocol.get("minimum_symbols", 80)),
                 long_fraction=.20, gross_limit=1., position_limit=.06, cost_bps=5.,
                 beta_exposure_limit=.10, rebalance_turnover_limit=.25, ic_floor=.005, seed=29)
    raw = pd.read_parquet(args.panel)
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    if raw.timestamp.max() > pd.Timestamp(protocol["contaminated_through"]):
        raise RuntimeError("Development panel contains observations after the contamination cutoff")
    frame = normalize(raw, cfg)
    features = list(read_json(args.model_audit).get("features", []))
    missing = sorted(set(features).difference(frame.columns))
    if not features or missing:
        raise RuntimeError(f"Frozen feature list absent or missing columns: {missing}")
    labeled = frame.dropna(subset=["forward_return"]).copy()
    labeled["rank_target"] = labeled.groupby("timestamp", observed=True)["forward_return"].rank(pct=True) - .5
    dates = sorted(labeled.timestamp.unique())
    if len(dates) < 504:
        raise RuntimeError("Insufficient frozen-development history")
    calibration_dates, fit_dates = dates[-126:], dates[:-126]
    fit_frame = labeled[labeled.timestamp.isin(fit_dates)]
    calibration = labeled[labeled.timestamp.isin(calibration_dates)].copy()
    models, calibration_ic = {}, {}
    for name, factory in (("elastic", _elastic), ("tree", _tree)):
        calibration_model = factory(cfg.seed)
        calibration_model.fit(fit_frame[features], fit_frame.rank_target)
        calibration[name] = pd.Series(calibration_model.predict(calibration[features]), index=calibration.index).groupby(calibration.timestamp).rank(pct=True) - .5
        daily = calibration.groupby("timestamp", observed=True).apply(lambda section: safe_rank_ic(section, name), include_groups=False).dropna()
        calibration_ic[name] = float(daily.mean()) if len(daily) else 0.0
        final_model = factory(cfg.seed)
        final_model.fit(labeled[features], labeled.rank_target)
        models[name] = final_model
    raw_weights = np.maximum(np.array([calibration_ic["elastic"], calibration_ic["tree"]]) - cfg.ic_floor, 0)
    if raw_weights.sum() <= 0:
        raise RuntimeError("Frozen calibration produced no positive ensemble edge")
    raw_weights /= raw_weights.sum()
    candidate = {
        "candidate_version": "v009-frozen-v007-1.0", "features": features, "models": models,
        "ensemble_weights": {"elastic": float(raw_weights[0]), "tree": float(raw_weights[1])},
        "calibration_ic": calibration_ic, "config": cfg.__dict__,
        "protocol_sha256": sha256(args.protocol), "universe_sha256": universe_hash,
        "sector_attestation_sha256": sha256(args.sector_attestation),
        "development_panel_sha256": sha256(args.panel), "training_rows": len(labeled),
        "training_periods": int(labeled.timestamp.nunique()),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(candidate, output)
    print(json.dumps({k: v for k, v in candidate.items() if k != "models"}, indent=2, default=str))
    print(f"Frozen candidate SHA256: {sha256(output)}")


if __name__ == "__main__":
    main()
