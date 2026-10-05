"""Low-risk factor study on the expanded V5.6 panel. No machine learning is involved.

Run from the project root with the virtual environment active:
    python low_risk_signal_study.py

Step 1  Combined score. low_risk = minus the average cross-sectional rank of
        volatility_63, volatility (20-day) and range_20, so a HIGHER score means a
        CALMER stock, which the IC report says should do better.
Step 2  Is it more than beta? On every date the score is regressed on sector
        dummies and beta (and, separately, also on size), and only the leftover
        part is tested. If the IC survives, the signal is not just beta/size in disguise.
Step 3  Backtest. The beta- and sector-neutral score goes straight into your V007
        portfolio constructor (sector-neutral long/short, beta band, turnover cap,
        transaction costs), rebalanced every 5 days, and is judged by the same gates
        as V008. Cost sensitivity, year-by-year results and long vs short legs are
        reported too.

Output: artifacts/v56-low-risk/ (report.json, ledger.parquet, yearly.csv).
Every number here uses 2018-2026, which you have already examined, so a pass makes
this a candidate for prospective shadow testing (V5.8), not a finished strategy.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from finai.research.v56.core import Config
from finai.research.v56.portfolio import metrics
from finai.research.v56.portfolio_v007 import simulate_v007

COMPONENTS = ["rank_volatility_63", "rank_volatility", "rank_range_20"]
RELATED = ["beta", "rank_volatility_63", "rank_volatility", "rank_range_20", "rank_amihud_20", "rank_log_market_cap"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default="data/research/v56-expanded/model_panel.parquet")
    p.add_argument("--output", default="artifacts/v56-low-risk")
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--cost-bps", type=float, default=5.0)
    p.add_argument("--sensitivity-costs", type=float, nargs="*", default=[10.0, 20.0])
    p.add_argument("--min-symbols", type=int, default=100)
    return p.parse_args()


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
    ranks = sub.groupby("timestamp")[[signal, target]].rank()
    ranks["timestamp"] = sub["timestamp"]
    centered = ranks[[signal, target]] - ranks.groupby("timestamp")[[signal, target]].transform("mean")
    centered["timestamp"] = sub["timestamp"]
    parts = pd.DataFrame({
        "timestamp": centered.timestamp,
        "xy": centered[signal] * centered[target],
        "xx": centered[signal] ** 2,
        "yy": centered[target] ** 2,
    }).groupby("timestamp")[["xy", "xx", "yy"]].sum()
    return (parts.xy / np.sqrt(parts.xx * parts.yy).replace(0, np.nan)).dropna()


def ic_summary(ic: pd.Series) -> dict:
    n, mean, std = len(ic), float(ic.mean()), float(ic.std(ddof=1))
    yearly = ic.groupby(ic.index.year).mean()
    return {"dates": n, "mean_ic": mean, "t_stat": mean / std * np.sqrt(n) if std > 0 else 0.0,
            "positive_years": f"{int((yearly > 0).sum())}/{len(yearly)}"}


def leg_returns(positions: pd.DataFrame, frame: pd.DataFrame) -> dict:
    merged = positions.merge(frame[["timestamp", "symbol", "forward_return"]], on=["timestamp", "symbol"])
    merged["contribution"] = merged.weight * merged.forward_return
    by_date = merged.assign(leg=np.where(merged.weight > 0, "long", np.where(merged.weight < 0, "short", "flat")))
    totals = by_date[by_date.leg != "flat"].groupby(["timestamp", "leg"]).contribution.sum().unstack(fill_value=0.0)
    return {f"{leg}_leg_compounded_gross": float((1 + totals[leg]).prod() - 1) for leg in totals.columns}


def run_backtest(pred: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    ledger, positions = simulate_v007(pred, cfg)
    ledger = ledger[ledger.timestamp.isin(pred.dropna(subset=["forward_return"]).timestamp.unique())]
    return ledger, positions, metrics(ledger, cfg.rebalance_every)


def main() -> None:
    args = parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    frame = pd.read_parquet(args.input)
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    frame = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    missing = [c for c in COMPONENTS + ["beta", "sector", "close"] if c not in frame.columns]
    if missing:
        raise SystemExit(f"Panel is missing columns {missing}; use the expanded panel from build_expanded_dataset.py")
    frame["forward_return"] = frame.groupby("symbol").close.transform(
        lambda s: s.shift(-args.horizon) / s - 1.0)
    counts = frame.groupby("timestamp").symbol.transform("nunique")
    frame = frame[counts >= args.min_symbols].copy()
    dates = np.array(sorted(frame.timestamp.unique()))
    scored = frame[frame.timestamp.isin(dates[:: args.horizon])].copy()
    print(f"Panel: {frame.symbol.nunique()} symbols, {len(dates)} dates; "
          f"{len(dates[::args.horizon])} non-overlapping {args.horizon}-day test dates")

    # ---- Step 1: combined score ------------------------------------------------
    for df in (frame, scored):
        df["low_risk"] = -df[COMPONENTS].mean(axis=1, skipna=False)
        df["low_risk"] = df.groupby("timestamp").low_risk.rank(pct=True) - 0.5

    print("Neutralizing target and score (this takes a few minutes)...")
    scored["resid_target"] = neutralize(scored, "forward_return", ["beta"])
    present = [c for c in RELATED if c in scored.columns]
    correlation = {}
    sample = scored[scored.timestamp.isin(dates[:: args.horizon * 4])]
    for a in present:
        correlation[a] = {b: 1.0 if a == b else
                          float(sample.groupby("timestamp")[[a, b]].corr(method="spearman").xs(b, level=1)[a].mean())
                          for b in present}
    print("\nAverage cross-sectional rank correlation between the passing features:")
    print(pd.DataFrame(correlation).round(2).to_string())

    # ---- Step 2: is it more than beta / size? ------------------------------------
    scored["low_risk_ex_beta"] = neutralize(scored, "low_risk", ["beta"])
    variants = {"combined score (as built)": "low_risk", "score with sector + beta removed": "low_risk_ex_beta"}
    if "rank_log_market_cap" in scored.columns:
        scored["low_risk_ex_beta_size"] = neutralize(scored, "low_risk", ["beta", "rank_log_market_cap"])
        variants["score with sector + beta + size removed"] = "low_risk_ex_beta_size"
    for component in COMPONENTS:
        scored[f"{component}_ex_beta"] = -neutralize(scored, component, ["beta"])
        variants[f"{component.removeprefix('rank_')} alone, beta removed (sign flipped)"] = f"{component}_ex_beta"
    ic_table = {label: ic_summary(rank_ic_by_date(scored, col, "resid_target")) for label, col in variants.items()}
    print(f"\nIC vs sector/beta-neutral {args.horizon}-day returns (positive = calmer stocks did better):")
    print(pd.DataFrame(ic_table).T.to_string(float_format=lambda v: f"{v:,.4f}"))

    # ---- Step 3: V007 backtest ----------------------------------------------------
    frame["score"] = neutralize(frame, "low_risk", ["beta"])
    frame["score"] = frame.groupby("timestamp").score.rank(pct=True) - 0.5
    pred = frame[["timestamp", "symbol", "sector", "beta", "forward_return", "score"]].rename(columns={"score": "ensemble"})
    pred = pred.dropna(subset=["ensemble"])
    cfg = Config(horizon=args.horizon, rebalance_every=args.horizon, min_symbols=args.min_symbols,
                 long_fraction=0.2, gross_limit=1.0, position_limit=0.02, cost_bps=args.cost_bps,
                 beta_exposure_limit=0.10, rebalance_turnover_limit=0.25)
    print(f"\nBacktesting through the V007 constructor at {args.cost_bps:g} bps...")
    ledger, positions, result = run_backtest(pred, cfg)
    gross_total = float((1 + ledger.gross_return).prod() - 1)
    active = float((ledger.construction_status == "active").mean())
    rebalance_ic = rank_ic_by_date(scored.assign(ensemble=scored.low_risk_ex_beta), "ensemble", "resid_target")
    checks = {
        "minimum_periods": len(ledger) >= 52,
        "active_fraction": active >= 0.80,
        "positive_residual_rank_ic": float(rebalance_ic.mean()) > 0,
        "positive_gross_return": gross_total > 0,
        "positive_net_return": result["cumulative_net_return"] > 0,
        "minimum_sharpe": result["annualized_sharpe"] >= 0.25,
        "maximum_drawdown": result["maximum_drawdown"] >= -0.30,
        "maximum_turnover": float(ledger.turnover.max()) <= cfg.rebalance_turnover_limit + 0.005,
        "beta_band": float(ledger.beta_exposure.abs().max()) <= cfg.beta_exposure_limit + 1e-8,
    }

    sensitivity = {}
    for bps in args.sensitivity_costs:
        alt = Config(**{**asdict(cfg), "cost_bps": bps})
        _, _, alt_result = run_backtest(pred, alt)
        sensitivity[f"{bps:g}_bps"] = {k: alt_result[k] for k in ("cumulative_net_return", "annualized_sharpe")}

    ledger["year"] = pd.to_datetime(ledger.timestamp).dt.year
    yearly = ledger.groupby("year").agg(
        periods=("net_return", "size"),
        gross_return=("gross_return", lambda r: (1 + r).prod() - 1),
        net_return=("net_return", lambda r: (1 + r).prod() - 1),
        mean_turnover=("turnover", "mean"),
    )
    legs = leg_returns(positions, frame)

    print(f"\nV007 backtest, {len(ledger)} rebalances, {args.cost_bps:g} bps per unit turnover:")
    for key in ("cumulative_net_return", "annualized_sharpe", "maximum_drawdown", "positive_period_fraction",
                "mean_turnover", "total_transaction_cost"):
        print(f"  {key:26s} {result[key]:,.4f}")
    print(f"  {'gross_compounded_return':26s} {gross_total:,.4f}")
    for key, value in legs.items():
        print(f"  {key:26s} {value:,.4f}")
    print("\nCost sensitivity:")
    for key, value in sensitivity.items():
        print(f"  {key:>8s}: net {value['cumulative_net_return']:,.4f}, Sharpe {value['annualized_sharpe']:,.3f}")
    print("\nYear by year:")
    print(yearly.to_string(float_format=lambda v: f"{v:,.4f}"))
    print("\nGates (same as V008):")
    for key, value in checks.items():
        print(f"  {'PASS' if value else 'FAIL'}  {key}")
    blocking = [k for k, v in checks.items() if not v]
    print("\nAll gates pass: candidate for a frozen config and prospective shadow testing."
          if not blocking else f"\nBlocking: {', '.join(blocking)}")

    ledger.to_parquet(out / "ledger.parquet", index=False)
    yearly.to_csv(out / "yearly.csv")
    report = {
        "study": "low_risk_composite", "components": COMPONENTS, "horizon": args.horizon,
        "development_window_previously_observed": True, "config": asdict(cfg),
        "feature_correlation": correlation, "ic_checks": ic_table, "metrics": result,
        "gross_compounded_return": gross_total, "active_fraction": active, "legs": legs,
        "cost_sensitivity": sensitivity, "checks": checks, "blocking_reasons": blocking,
        "next_step": "If all gates pass: freeze this exact config, then run it prospectively (V5.8 shadow) "
                     "on data that does not exist yet. Do not tune it further on 2018-2026.",
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nWritten: {out / 'report.json'}, {out / 'ledger.parquet'}, {out / 'yearly.csv'}")


if __name__ == "__main__":
    main()
