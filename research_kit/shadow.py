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


def report() -> None:
    strategies = frozen_strategies()
    if not strategies:
        print("No frozen strategies.")
        return
    for frozen in strategies:
        spec, hid = frozen["spec"], frozen["id"]
        horizon, cost = int(spec["horizon"]), float(spec.get("cost_bps", 5.0))
        book_path = SHADOW / hid / "book.parquet"
        print(f"\n=== {hid} ({frozen['status']}, frozen on data through {frozen['freeze_data_date'][:10]}) ===")
        if not book_path.exists():
            print("  No shadow rebalances recorded yet.")
            continue
        book = pd.read_parquet(book_path)
        panel = load_panel(spec)
        closes = panel.pivot_table(index="timestamp", columns="symbol", values="close")
        dates = list(closes.index)
        rows, previous = [], pd.Series(dtype=float)
        for date, positions in book.groupby("timestamp", sort=True):
            weights = positions.set_index("symbol").weight
            union = weights.index.union(previous.index)
            turnover = float((weights.reindex(union, fill_value=0) - previous.reindex(union, fill_value=0)).abs().sum())
            previous = weights
            position = dates.index(pd.Timestamp(date)) if pd.Timestamp(date) in dates else None
            if position is None or position + horizon >= len(dates):
                rows.append({"timestamp": date, "status": "pending", "turnover": turnover})
                continue
            start, end = closes.iloc[position], closes.iloc[position + horizon]
            returns = (end / start - 1.0).reindex(weights.index).fillna(0.0)
            gross = float((weights * returns).sum())
            rows.append({"timestamp": date, "status": "complete", "gross_return": gross, "turnover": turnover,
                         "cost": turnover * cost / 1e4, "net_return": gross - turnover * cost / 1e4})
        ledger = pd.DataFrame(rows)
        done = ledger[ledger.status == "complete"]
        needed = int(spec.get("forward", {}).get("min_periods", 24))
        print(f"  Rebalances recorded: {len(ledger)}; completed: {len(done)}; needed for a verdict: {needed}")
        summary = {"completed": len(done), "needed": needed}
        if len(done) >= 2:
            m = metrics(done.assign(net_return=done.net_return), horizon)
            r = done.net_return
            t_stat = float(r.mean() / r.std(ddof=1) * np.sqrt(len(r))) if r.std(ddof=1) > 0 else 0.0
            summary.update({"net_return": m["cumulative_net_return"], "sharpe": m["annualized_sharpe"],
                            "max_drawdown": m["maximum_drawdown"], "t_stat": t_stat,
                            "hit_rate": float((r > 0).mean())})
            print(f"  Shadow so far: net {m['cumulative_net_return']:+.2%}, Sharpe {m['annualized_sharpe']:.2f}, "
                  f"max drawdown {m['maximum_drawdown']:.2%}, t-stat {t_stat:.2f}, hit rate {(r > 0).mean():.0%}")
            historical = RESEARCH / "results" / hid / "result.json"
            if historical.exists():
                h = json.loads(historical.read_text(encoding="utf-8"))["metrics"]
                print(f"  Historical test for comparison: Sharpe {h['annualized_sharpe']:.2f}, "
                      f"net {h['cumulative_net_return']:+.2%} over the whole window")
        gates = spec.get("gates", {})
        if len(done) < needed:
            verdict = f"collecting evidence ({len(done)}/{needed}) - do not judge yet"
        elif frozen["status"] != "qualified":
            verdict = "exploratory: enough data to look at, but it can never be promoted"
        elif summary.get("sharpe", 0) >= gates.get("min_sharpe", 0.25) and summary.get("net_return", 0) > 0:
            verdict = "forward evidence supports the historical result - candidate for human champion review"
        else:
            verdict = "forward evidence does NOT support the historical result - retire this strategy"
        print(f"  Verdict: {verdict}")
        summary["verdict"] = verdict
        out = SHADOW / hid
        ledger.to_csv(out / "ledger.csv", index=False)
        (out / "report.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
