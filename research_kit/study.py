"""One-shot historical test of a registered hypothesis (generalized low-risk study)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from finai.research.v56.core import Config
from finai.research.v56.portfolio import metrics
from finai.research.v56.portfolio_v007 import simulate_v007

from . import RESEARCH

DEFAULT_CONSTRUCTION = {"long_fraction": 0.2, "gross_limit": 1.0, "position_limit": 0.02,
                        "beta_exposure_limit": 0.10, "rebalance_turnover_limit": 0.25}
DEFAULT_GATES = {"min_periods": 52, "min_active_fraction": 0.80, "min_neutral_ic_t": 2.5,
                 "min_sharpe": 0.25, "max_drawdown": -0.30, "must_survive_cost_bps": 10.0}


# ----------------------------------------------------------------------------- helpers
def neutralize(frame: pd.DataFrame, column: str, controls: list[str]) -> pd.Series:
    """Per date: residual of `column` after OLS on sector dummies plus numeric controls."""
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    need = [column, "sector"] + controls
    valid = frame[need].notna().all(axis=1)
    for _, section in frame.loc[valid, need].groupby(frame.loc[valid, "timestamp"], sort=False):
        if len(section) < 30:
            continue
        dummies = pd.get_dummies(section["sector"], dtype=float).to_numpy()
        design = np.column_stack([dummies] + [section[c].to_numpy(float) for c in controls])
        y = section[column].to_numpy(float)
        coef = np.linalg.lstsq(design, y, rcond=None)[0]
        out.loc[section.index] = y - design @ coef
    return out


def rank_ic_by_date(frame: pd.DataFrame, signal: str, target: str) -> pd.Series:
    sub = frame[["timestamp", signal, target]].dropna()
    if sub.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    ranks = sub.groupby("timestamp")[[signal, target]].rank()
    centered = ranks - ranks.groupby(sub["timestamp"]).transform("mean")
    parts = pd.DataFrame({"timestamp": sub["timestamp"], "xy": centered[signal] * centered[target],
                          "xx": centered[signal] ** 2, "yy": centered[target] ** 2})
    sums = parts.groupby("timestamp")[["xy", "xx", "yy"]].sum()
    return (sums.xy / np.sqrt(sums.xx * sums.yy).replace(0, np.nan)).dropna()


def ic_summary(ic: pd.Series) -> dict:
    n = len(ic)
    if n < 3:
        return {"dates": n, "mean_ic": float("nan"), "t_stat": 0.0, "positive_years": "0/0"}
    mean, std = float(ic.mean()), float(ic.std(ddof=1))
    yearly = ic.groupby(ic.index.year).mean()
    return {"dates": n, "mean_ic": mean, "t_stat": mean / std * np.sqrt(n) if std > 0 else 0.0,
            "positive_years": f"{int((yearly > 0).sum())}/{len(yearly)}"}


def signal_score(frame: pd.DataFrame, signal: dict) -> pd.Series:
    """Weighted sum of (already centered) rank columns, missing values filled, re-ranked
    per date, then neutralized against the listed controls and re-ranked again."""
    fill = float(signal.get("fill_missing", 0.0))
    raw = sum(float(w) * frame[c].astype(float).fillna(fill) for c, w in signal["columns"].items())
    work = frame[["timestamp", "sector"] + [c for c in signal.get("neutralize", []) if c in frame]].copy()
    work["raw"] = raw.groupby(frame["timestamp"]).rank(pct=True) - 0.5
    controls = [c for c in signal.get("neutralize", []) if c in frame]
    if controls:
        work["raw"] = neutralize(work, "raw", controls)
    return work["raw"].groupby(frame["timestamp"]).rank(pct=True) - 0.5


def load_panel(spec: dict) -> pd.DataFrame:
    path = Path(spec["panel"])
    if not path.exists():
        raise SystemExit(f"Panel not found: {path}. Build it first (see research_kit/README.md).")
    frame = pd.read_parquet(path)
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    missing = [c for c in list(spec["signal"]["columns"]) + ["beta", "sector", "close"] if c not in frame]
    if missing:
        raise SystemExit(f"Panel {path} is missing columns {missing}. Did you run build-events?")
    return frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def make_config(spec: dict, cost_bps: float) -> Config:
    c = {**DEFAULT_CONSTRUCTION, **spec.get("construction", {})}
    return Config(horizon=int(spec["horizon"]), rebalance_every=int(spec["horizon"]),
                  min_symbols=int(spec.get("min_symbols", 100)), cost_bps=float(cost_bps), **c)


# ----------------------------------------------------------------------------- study
def run_study(spec: dict) -> dict:
    horizon = int(spec["horizon"])
    frame = load_panel(spec)
    start = pd.Timestamp(spec["window"]["start"], tz="UTC")
    end = pd.Timestamp(spec["window"]["end"], tz="UTC")
    frame["forward_return"] = frame.groupby("symbol").close.transform(lambda s: s.shift(-horizon) / s - 1.0)
    frame = frame[(frame.timestamp >= start) & (frame.timestamp <= end)].copy()
    # Returns that would end after the window are not part of this test.
    dates = np.array(sorted(frame.timestamp.unique()))
    if len(dates) <= horizon:
        raise SystemExit("Window is too short for this horizon.")
    frame.loc[frame.timestamp > dates[-horizon - 1], "forward_return"] = np.nan
    counts = frame.groupby("timestamp").symbol.transform("nunique")
    frame = frame[counts >= int(spec.get("min_symbols", 100))].copy()
    dates = np.array(sorted(frame.timestamp.unique()))
    print(f"Window {dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d}: {frame.symbol.nunique()} symbols, "
          f"{len(dates)} dates; horizon {horizon}")

    print("Building score and neutral target (a few minutes)...")
    frame["score"] = signal_score(frame, spec["signal"])
    sampled = frame[frame.timestamp.isin(dates[::horizon])].copy()
    sampled["resid_target"] = neutralize(sampled, "forward_return", ["beta"])
    unneutral = {**spec["signal"], "neutralize": []}
    sampled["score_unneutral"] = signal_score(sampled, unneutral)
    ic_checks = {"score before neutralization": ic_summary(rank_ic_by_date(sampled, "score_unneutral", "resid_target")),
                 "score, sector + beta neutral": ic_summary(rank_ic_by_date(sampled, "score", "resid_target"))}
    if "rank_log_market_cap" in sampled:
        sampled["score_ex_size"] = neutralize(sampled, "score", ["beta", "rank_log_market_cap"])
        ic_checks["score, sector + beta + size neutral"] = ic_summary(
            rank_ic_by_date(sampled, "score_ex_size", "resid_target"))

    pred = frame[["timestamp", "symbol", "sector", "beta", "forward_return", "score"]].rename(columns={"score": "ensemble"})
    pred = pred.dropna(subset=["ensemble"])
    base_cost = float(spec.get("cost_bps", 5.0))
    cfg = make_config(spec, base_cost)
    ledger, positions = simulate_v007(pred, cfg)
    ledger = ledger[ledger.timestamp.isin(pred.dropna(subset=["forward_return"]).timestamp.unique())].copy()
    result = metrics(ledger, cfg.rebalance_every)
    gross_total = float((1 + ledger.gross_return).prod() - 1)
    active = float(ledger.construction_status.isin(["active", "beta_drift_limited"]).mean())

    sensitivity = {}
    for bps in sorted(set(spec.get("sensitivity_costs", [10.0, 20.0]))):
        alt_ledger, _ = simulate_v007(pred, make_config(spec, bps))
        alt_ledger = alt_ledger[alt_ledger.timestamp.isin(ledger.timestamp)]
        alt = metrics(alt_ledger, cfg.rebalance_every)
        sensitivity[f"{bps:g}"] = {"net": alt["cumulative_net_return"], "sharpe": alt["annualized_sharpe"]}

    ledger["year"] = pd.to_datetime(ledger.timestamp).dt.year
    yearly = ledger.groupby("year").agg(
        periods=("net_return", "size"),
        gross=("gross_return", lambda r: (1 + r).prod() - 1),
        net=("net_return", lambda r: (1 + r).prod() - 1),
        turnover=("turnover", "mean"))

    g = {**DEFAULT_GATES, **spec.get("gates", {})}
    survive_key = f"{float(g['must_survive_cost_bps']):g}"
    survive_net = sensitivity.get(survive_key, {}).get("net")
    if survive_net is None:
        alt_ledger, _ = simulate_v007(pred, make_config(spec, g["must_survive_cost_bps"]))
        survive_net = float((1 + alt_ledger[alt_ledger.timestamp.isin(ledger.timestamp)].net_return).prod() - 1)
    neutral_t = ic_checks["score, sector + beta neutral"]["t_stat"]
    checks = {
        "minimum_periods": len(ledger) >= g["min_periods"],
        "active_fraction": active >= g["min_active_fraction"],
        "neutral_ic_t_stat": neutral_t >= g["min_neutral_ic_t"],
        "positive_gross_return": gross_total > 0,
        "positive_net_return": result["cumulative_net_return"] > 0,
        "minimum_sharpe": result["annualized_sharpe"] >= g["min_sharpe"],
        "maximum_drawdown": result["maximum_drawdown"] >= g["max_drawdown"],
        "maximum_turnover": float(ledger.turnover.max()) <= cfg.rebalance_turnover_limit + 0.005,
        "beta_band": float(ledger.beta_exposure.abs().max()) <= cfg.beta_exposure_limit + 1e-6,
        f"positive_net_at_{survive_key}_bps": survive_net > 0,
    }
    return {"ic_checks": ic_checks, "metrics": result, "gross_compounded_return": gross_total,
            "active_fraction": active, "cost_sensitivity": sensitivity,
            "yearly": yearly.reset_index().to_dict(orient="records"), "checks": checks,
            "passed": all(checks.values()), "blocking": [k for k, v in checks.items() if not v],
            "config": asdict(cfg), "rebalances": len(ledger)}


def print_result(spec: dict, r: dict) -> None:
    print("\nIC vs sector/beta-neutral forward returns:")
    print(pd.DataFrame(r["ic_checks"]).T.to_string(float_format=lambda v: f"{v:,.4f}"))
    m = r["metrics"]
    print(f"\nBacktest ({r['rebalances']} rebalances every {spec['horizon']} days, {spec.get('cost_bps', 5)} bps):")
    for key in ("cumulative_net_return", "annualized_sharpe", "maximum_drawdown", "positive_period_fraction",
                "mean_turnover", "total_transaction_cost"):
        print(f"  {key:26s} {m[key]:,.4f}")
    print(f"  {'gross_compounded_return':26s} {r['gross_compounded_return']:,.4f}")
    print("\nCost sensitivity:")
    for bps, v in r["cost_sensitivity"].items():
        print(f"  {bps:>5s} bps: net {v['net']:,.4f}, Sharpe {v['sharpe']:,.3f}")
    print("\nYear by year:")
    print(pd.DataFrame(r["yearly"]).to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    print("\nGates:")
    for key, value in r["checks"].items():
        print(f"  {'PASS' if value else 'FAIL'}  {key}")
    print(f"\nDecision rule (registered in advance): {spec['decision_rule']}")
    print("RESULT: PASSED - eligible to freeze." if r["passed"]
          else f"RESULT: FAILED ({', '.join(r['blocking'])}). Per the decision rule, close this hypothesis.")


def save_result(spec: dict, r: dict) -> Path:
    out = RESEARCH / "results" / spec["id"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(r, indent=2, default=str), encoding="utf-8")
    return out / "result.json"
