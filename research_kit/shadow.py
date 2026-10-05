"""Forward (shadow) testing: freeze a strategy, then record its portfolio on new data only.

Nothing is traded. Each run appends the portfolio the frozen strategy would hold to
research/shadow/<id>/book.parquet. shadow-report later scores those books against prices
that did not exist when the strategy was frozen - the only truly out-of-sample evidence.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from finai.research.v56.portfolio import metrics
from finai.research.v56.portfolio_v007 import alpha_preserving_weights

from . import RESEARCH, registry
from .study import load_panel, make_config, signal_score

FROZEN = RESEARCH / "frozen"
SHADOW = RESEARCH / "shadow"


def log(message: str) -> None:
    line = f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}Z] {message}"
    print(line, flush=True)
    SHADOW.mkdir(parents=True, exist_ok=True)
    with (SHADOW / "run.log").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def frozen_strategies() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FROZEN.glob("*.json"))]


def freeze(hypothesis_id: str, exploratory: bool) -> None:
    spec = registry.registered_spec(hypothesis_id)
    forward = spec.get("forward", {})
    if not forward.get("ready", True):
        raise SystemExit(f"'{hypothesis_id}' cannot be forward-tested yet: {forward.get('reason', 'not ready')}")
    path = FROZEN / f"{hypothesis_id}.json"
    if path.exists():
        raise SystemExit(f"'{hypothesis_id}' is already frozen ({path}). Frozen strategies are never edited.")
    tests = [e for e in registry.events(hypothesis_id) if e["event"] == "tested"]
    if not exploratory:
        if not tests:
            raise SystemExit("Run the one-shot historical test first: python -m research_kit test " + hypothesis_id)
        if not tests[-1]["passed"]:
            raise SystemExit(f"'{hypothesis_id}' failed its historical test, so it cannot be frozen as a qualified "
                             "candidate. Use --exploratory to watch it forward anyway; exploratory strategies "
                             "can never become a champion.")
    panel = load_panel(spec)
    freeze_date = panel.timestamp.max()
    record = {"id": hypothesis_id, "spec": spec, "spec_hash": registry.spec_hash(spec),
              "status": "exploratory" if exploratory else "qualified", "frozen_at": registry.now(),
              "freeze_data_date": str(freeze_date), "git_commit": registry.git_commit()}
    FROZEN.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    registry.append({"event": "frozen", "id": hypothesis_id, "status": record["status"],
                     "freeze_data_date": record["freeze_data_date"], "timestamp": record["frozen_at"],
                     "git_commit": record["git_commit"]})
    print(f"Frozen '{hypothesis_id}' as {record['status']}. Only data after {freeze_date:%Y-%m-%d} will count.")
    print("Next: python -m research_kit shadow-run  (and schedule it weekly with research_kit\\schedule_shadow.ps1)")


def refresh_data() -> None:
    from . import events
    log("Refreshing market data and fundamentals (30-60 minutes)...")
    result = subprocess.run([sys.executable, "build_expanded_dataset.py", "all", "--refresh-days", "6"])
    if result.returncode != 0:
        raise SystemExit("Data refresh failed; see the output above. Nothing was recorded.")
    log("Refreshing SEC event data...")
    events.build_sue(refresh_days=6)
    events.build_insiders(start="2018-01-01")
    events.build_panel_v2()


def run(skip_refresh: bool) -> None:
    strategies = frozen_strategies()
    if not strategies:
        print("No frozen strategies. Freeze one first: python -m research_kit freeze <id> [--exploratory]")
        return
    if not skip_refresh:
        refresh_data()
    for frozen in strategies:
        spec, hid = frozen["spec"], frozen["id"]
        verdict = final_verdict(hid)
        if verdict and verdict["outcome"] == "retired":
            log(f"{hid}: retired on {verdict['timestamp'][:10]} ({verdict['reason']}); no longer recorded.")
            continue
        if registry.spec_hash(spec) != frozen["spec_hash"]:
            log(f"{hid}: frozen spec was modified after freezing - skipped. Restore the original file.")
            continue
        panel = load_panel(spec)
        latest = panel.timestamp.max()
        freeze_date = pd.Timestamp(frozen["freeze_data_date"])
        if latest <= freeze_date:
            log(f"{hid}: no data after the freeze date yet ({latest:%Y-%m-%d}).")
            continue
        book_path = SHADOW / hid / "book.parquet"
        book = pd.read_parquet(book_path) if book_path.exists() else pd.DataFrame()
        dates = np.array(sorted(panel.timestamp.unique()))
        if not book.empty:
            last = pd.Timestamp(book.timestamp.max())
            elapsed = int((dates > last).sum())
            if elapsed < int(spec["horizon"]):
                log(f"{hid}: {elapsed} trading days since the last rebalance ({last:%Y-%m-%d}); "
                    f"next after {spec['horizon']}.")
                continue
        section = panel[panel.timestamp == latest].copy().reset_index(drop=True)
        section["score"] = signal_score(section, spec["signal"]).to_numpy()
        section = section.sort_values("symbol").reset_index(drop=True)
        previous_map = {} if book.empty else book[book.timestamp == book.timestamp.max()].set_index("symbol").weight.to_dict()
        previous = np.array([previous_map.get(s, 0.0) for s in section.symbol])
        cfg = make_config(spec, float(spec.get("cost_bps", 5.0)))
        weights, status = alpha_preserving_weights(section.score.to_numpy(float), previous,
                                                   section.beta.to_numpy(float), section.sector.to_numpy(), cfg)
        rows = pd.DataFrame({"timestamp": latest, "symbol": section.symbol, "weight": weights,
                             "score": section.score, "status": status, "spec_hash": frozen["spec_hash"]})
        book = pd.concat([book, rows], ignore_index=True)
        book_path.parent.mkdir(parents=True, exist_ok=True)
        book.to_parquet(book_path, index=False)
        registry.append({"event": "shadow_rebalance", "id": hid, "data_date": str(latest), "status": status,
                         "positions": int((np.abs(weights) > 1e-9).sum()), "timestamp": registry.now()})
        log(f"{hid}: recorded rebalance for {latest:%Y-%m-%d} ({status}, "
            f"{int((weights > 0).sum())} long / {int((weights < 0).sum())} short).")


# ----------------------------------------------------------------------------- evaluation
# Fixed, pre-declared evaluation rules (version 1). They are written into every report so a
# verdict can always be traced to the exact rule that produced it. Early stopping is allowed
# ONLY for failure: looking at results every day and stopping on a good streak would make a
# lucky run look like proof, so a positive verdict is only possible at the planned length.
EVALUATION_RULES = {
    "version": 1,
    "early_retire_after_periods": 6,
    "early_retire_drawdown_multiple": 2.0,      # forward drawdown worse than 2x the historical one
    "early_retire_drawdown_floor": -0.15,       # used when there is no historical drawdown
    "early_retire_t_vs_backtest": -2.5,         # clearly worse than the backtest predicted
    "final_t_vs_backtest_floor": -1.5,          # at the end: not meaningfully worse than the backtest
    "final_requires_positive_net": True,
    "final_requires_min_sharpe": True,
}


def final_verdict(hypothesis_id: str) -> dict | None:
    found = [e for e in registry.events(hypothesis_id) if e["event"] == "verdict"]
    return found[-1] if found else None


def shadow_ledger(frozen: dict, panel: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Completed and pending shadow periods, plus mark-to-market of the open period."""
    spec = frozen["spec"]
    horizon, cost = int(spec["horizon"]), float(spec.get("cost_bps", 5.0))
    book_path = SHADOW / frozen["id"] / "book.parquet"
    if not book_path.exists():
        return pd.DataFrame(), {}
    book = pd.read_parquet(book_path)
    panel = load_panel(spec) if panel is None else panel
    closes = panel.pivot_table(index="timestamp", columns="symbol", values="close")
    dates = list(closes.index)
    rows, previous, open_position = [], pd.Series(dtype=float), {}
    for date, positions in book.groupby("timestamp", sort=True):
        weights = positions.set_index("symbol").weight
        union = weights.index.union(previous.index)
        turnover = float((weights.reindex(union, fill_value=0) - previous.reindex(union, fill_value=0)).abs().sum())
        previous = weights
        stamp = pd.Timestamp(date)
        position = dates.index(stamp) if stamp in dates else None
        if position is None:
            rows.append({"timestamp": stamp, "status": "pending", "turnover": turnover})
            continue
        last = min(position + horizon, len(dates) - 1)
        returns = (closes.iloc[last] / closes.iloc[position] - 1.0).reindex(weights.index).fillna(0.0)
        gross = float((weights * returns).sum())
        if position + horizon < len(dates):
            rows.append({"timestamp": stamp, "status": "complete", "gross_return": gross, "turnover": turnover,
                         "cost": turnover * cost / 1e4, "net_return": gross - turnover * cost / 1e4})
        else:
            rows.append({"timestamp": stamp, "status": "pending", "turnover": turnover})
            open_position = {"since": str(stamp.date()), "days_held": last - position,
                             "unrealized_gross": gross, "as_of": str(dates[-1].date())}
    return pd.DataFrame(rows), open_position


def evaluate(frozen: dict, panel: pd.DataFrame | None = None) -> dict:
    spec, hid = frozen["spec"], frozen["id"]
    horizon = int(spec["horizon"])
    rules = EVALUATION_RULES
    needed = int(spec.get("forward", {}).get("min_periods", 24))
    min_sharpe = float(spec.get("gates", {}).get("min_sharpe", 0.25))
    ledger, open_position = shadow_ledger(frozen, panel)
    done = ledger[ledger.status == "complete"] if not ledger.empty else ledger
    out = {"id": hid, "status_class": frozen["status"], "rules": rules, "completed": len(done), "needed": needed,
           "open_period": open_position, "as_of": registry.now()}
    historical_file = RESEARCH / "results" / hid / "result.json"
    hist_mean, hist_dd = 0.0, None
    if historical_file.exists():
        h = json.loads(historical_file.read_text(encoding="utf-8"))["metrics"]
        if h.get("period_count"):
            hist_mean = (1 + h["cumulative_net_return"]) ** (1 / h["period_count"]) - 1
        hist_dd = h.get("maximum_drawdown")
        out["historical"] = {"mean_per_period": hist_mean, "max_drawdown": hist_dd,
                             "sharpe": h.get("annualized_sharpe")}
    previous = final_verdict(hid)
    if previous:
        out.update({"verdict": previous["outcome"], "final": True,
                    "reason": f"FINAL since {previous['timestamp'][:10]} after {previous['completed_periods']} "
                              f"periods: {previous['reason']} (figures above keep updating for monitoring)"})
    if len(done) >= 2:
        r = done.net_return.astype(float)
        m = metrics(done, horizon)
        sd = float(r.std(ddof=1))
        t_zero = float(r.mean() / sd * np.sqrt(len(r))) if sd > 0 else 0.0
        t_vs_hist = float((r.mean() - hist_mean) / sd * np.sqrt(len(r))) if sd > 0 else 0.0
        out.update({"net_return": m["cumulative_net_return"], "sharpe": m["annualized_sharpe"],
                    "max_drawdown": m["maximum_drawdown"], "t_stat": t_zero, "t_vs_backtest": t_vs_hist,
                    "hit_rate": float((r > 0).mean())})
    if previous:
        _write_report(hid, ledger, out)
        return out
    dd_limit = (rules["early_retire_drawdown_multiple"] * hist_dd) if hist_dd else rules["early_retire_drawdown_floor"]
    outcome, reason = None, None
    n = len(done)
    if n >= rules["early_retire_after_periods"] and n < needed:
        if out.get("max_drawdown", 0) < dd_limit:
            outcome, reason = "retired", f"drawdown {out['max_drawdown']:.1%} breached the limit {dd_limit:.1%}"
        elif out.get("t_vs_backtest", 0) < rules["early_retire_t_vs_backtest"]:
            outcome, reason = "retired", (f"performing significantly worse than the backtest "
                                          f"(t = {out['t_vs_backtest']:.2f})")
    elif n >= needed:
        ok = (out.get("net_return", 0) > 0 and out.get("sharpe", 0) >= min_sharpe
              and out.get("t_vs_backtest", 0) >= rules["final_t_vs_backtest_floor"])
        if ok and frozen["status"] == "qualified":
            outcome, reason = "supported", "forward results confirm the backtest; ready for human champion review"
        elif ok:
            outcome, reason = "informative", ("forward results look good, but this strategy is exploratory; "
                                              "register a NEW hypothesis to test it properly on later data")
        else:
            outcome, reason = "retired", (f"after {n} periods: net {out.get('net_return', 0):+.2%}, "
                                          f"Sharpe {out.get('sharpe', 0):.2f}, t vs backtest "
                                          f"{out.get('t_vs_backtest', 0):.2f}")
    if outcome:
        snapshot = {k: out.get(k) for k in ("net_return", "sharpe", "max_drawdown", "t_stat", "t_vs_backtest")}
        registry.append({"event": "verdict", "id": hid, "outcome": outcome, "reason": reason,
                         "completed_periods": n, "metrics_at_verdict": snapshot,
                         "rules_version": rules["version"], "timestamp": registry.now()})
        out.update({"verdict": outcome, "reason": reason, "final": True, "new_verdict": True})
    else:
        out.update({"verdict": "collecting", "final": False,
                    "reason": f"{n}/{needed} completed periods; early retirement possible from period "
                              f"{rules['early_retire_after_periods']}, a positive verdict only at {needed}"})
    _write_report(hid, ledger, out)
    return out


def _write_report(hid: str, ledger: pd.DataFrame, out: dict) -> None:
    out_dir = SHADOW / hid
    out_dir.mkdir(parents=True, exist_ok=True)
    if not ledger.empty:
        ledger.to_csv(out_dir / "ledger.csv", index=False)
    (out_dir / "report.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")


def describe(result: dict) -> str:
    parts = [f"{result['id']} [{result['status_class']}]: {result['verdict'].upper()}",
             f"{result['completed']}/{result['needed']} periods"]
    if "net_return" in result:
        parts.append(f"net {result['net_return']:+.2%}, Sharpe {result['sharpe']:.2f}, "
                     f"max DD {result['max_drawdown']:.1%}, t vs backtest {result['t_vs_backtest']:.2f}")
    if result.get("open_period"):
        o = result["open_period"]
        parts.append(f"open period since {o['since']}: {o['unrealized_gross']:+.2%} (day {o['days_held']})")
    return " | ".join(parts) + f"\n    {result['reason']}"


def report() -> list[dict]:
    strategies = frozen_strategies()
    if not strategies:
        print("No frozen strategies.")
        return []
    results = []
    for frozen in strategies:
        result = evaluate(frozen)
        print(describe(result))
        results.append(result)
    return results
