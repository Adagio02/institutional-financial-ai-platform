"""Walk-forward calibration of stop distances, with a plateau check and a one-time
validation on stocks the calibration never touched.

1. Grid: a small, pre-registered set of ATR stop multiples (e.g. 2, 2.5, 3).
2. Walk-forward: for each year, the setting is chosen using ONLY earlier years, by a
   smoothed score (a setting's Sharpe averaged with its grid neighbours, which favours
   plateaus over isolated peaks). The test result is the stitched string of those
   next-year results, never the best in-sample result.
3. Plateau: every grid setting must point the same way, and the weakest must reach a
   pre-registered fraction of the best; otherwise the "best" setting is likely luck.
4. Validation: the setting chosen on all S&P 500 data is run ONCE on S&P 400 mid-caps,
   which the calibration never saw. Then, as always, a forward test.
"""
from __future__ import annotations

import copy
import io
import json

import numpy as np
import pandas as pd

import build_expanded_dataset as bx

from . import DATA, RESEARCH, registry, strategies as S

MIDCAP = DATA.parent / "midcap"
MIDCAP_LIST_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"


def log(message: str) -> None:
    print(message, flush=True)


def with_setting(spec: dict, k: float) -> dict:
    out = copy.deepcopy(spec)
    out["rule"]["stop_atr"] = float(k)
    out["rule"]["trail_atr"] = float(k) * float(spec["rule"]["trail_multiple_of_stop"])
    return out


def selected_setting(spec: dict) -> float:
    path = RESEARCH / "results" / spec["id"] / "result.json"
    if not path.exists():
        raise SystemExit(f"No calibration result for {spec['id']}; run: python -m research_kit test {spec['id']}")
    return float(json.loads(path.read_text(encoding="utf-8"))["final_choice"])


def engine(spec: dict, cost_bps: float, data: dict | None = None) -> dict:
    """The frozen strategy: the breakout rules with the setting the calibration chose."""
    return S.breakout_stops(with_setting(spec, selected_setting(spec)), cost_bps, data)


def sharpe(daily: pd.Series) -> float:
    sd = daily.std(ddof=1)
    return float(daily.mean() / sd * np.sqrt(S.YEAR)) if len(daily) > 20 and sd > 0 else 0.0


def smoothed_choice(grid: list[float], scores: dict[float, float]) -> float:
    smooth = {}
    for i, k in enumerate(grid):
        neighbours = [scores[grid[j]] for j in (i - 1, i, i + 1) if 0 <= j < len(grid)]
        smooth[k] = float(np.mean(neighbours))
    return max(grid, key=lambda k: (smooth[k], -abs(k - grid[len(grid) // 2])))


def run_test(spec: dict) -> dict:
    cal = spec["calibration"]
    grid = [float(k) for k in cal["grid"]]
    data = S.load_stocks()
    costs = [float(spec["cost_bps"])] + [float(b) for b in spec.get("sensitivity_costs", [])]
    runs = {}
    for k in grid:
        for bps in costs:
            log(f"  Running stop = {k:g} x ATR at {bps:g} bps...")
            runs[(k, bps)] = S.breakout_stops(with_setting(spec, k), bps, data)
    base = float(spec["cost_bps"])
    series = {k: S.window(runs[(k, base)]["ledger"].net, spec) for k in grid}
    years = sorted(set(series[grid[0]].index.year))
    first_oos = int(cal["first_test_year"])
    selections, stitched, trades = {}, {bps: [] for bps in costs}, []
    for year in [y for y in years if y >= first_oos]:
        scores = {k: sharpe(series[k][series[k].index.year < year]) for k in grid}
        choice = smoothed_choice(grid, scores)
        selections[str(year)] = {"chosen": choice, "training_sharpes": {f"{k:g}": round(v, 3) for k, v in scores.items()}}
        for bps in costs:
            s = S.window(runs[(choice, bps)]["ledger"].net, spec)
            stitched[bps].append(s[s.index.year == year])
        t = runs[(choice, base)]["trades"]
        if not t.empty:
            trades.append(t[pd.to_datetime(t.entry_date).dt.year == year])
    oos = {bps: pd.concat(parts) for bps, parts in stitched.items()}
    net = oos[base]
    spy = S.window(runs[(grid[0], base)]["benchmarks"]["SPY"], spec).reindex(net.index).fillna(0.0)
    full = {k: sharpe(series[k]) for k in grid}
    best, worst = max(full.values()), min(full.values())
    plateau_ok = best > 0 and worst > 0 and worst >= float(cal["plateau_min_ratio"]) * best
    trade_frame = pd.concat(trades) if trades else pd.DataFrame()
    result = {"strategy_type": spec["strategy_type"], "metrics": S.perf(net), "benchmarks": {"SPY": S.perf(spy)},
              "excess_t_vs": {"SPY": S.excess_t(net, spy)},
              "yearly": {str(y): float(v) for y, v in ((1 + net).groupby(net.index.year).prod() - 1).items()},
              "cost_sensitivity": {f"{b:g}": S.perf(oos[b]) for b in costs[1:]}, "trades": S.trade_stats(trade_frame),
              "stats": {"out_of_sample_years": list(selections)}, "ic_checks": {},
              "selections": selections, "full_period_sharpe_by_setting": {f"{k:g}": round(v, 3) for k, v in full.items()},
              "final_choice": smoothed_choice(grid, full), "plateau_ok": plateau_ok}
    g = spec["gates"]
    worst_bps = f"{max(costs):g}"
    result["checks"] = {
        "minimum_out_of_sample_months": result["metrics"].get("months", 0) >= g["min_months"],
        "positive_net_return": result["metrics"].get("total_return", -1) > 0,
        f"positive_net_at_{worst_bps}_bps": result["cost_sensitivity"].get(worst_bps, {}).get("total_return", -1) > 0,
        "minimum_trades": result["trades"].get("trades", 0) >= g["min_trades"],
        "profit_factor": result["trades"].get("profit_factor", 0) >= g["min_profit_factor"],
        "sharpe_at_least_spy": result["metrics"].get("sharpe", 0) >= result["benchmarks"]["SPY"].get("sharpe", 0),
        "maximum_drawdown": result["metrics"].get("max_drawdown", -1) >= g["max_drawdown"],
        "plateau_not_peak": plateau_ok,
    }
    result["passed"] = all(result["checks"].values())
    result["blocking"] = [k for k, ok in result["checks"].items() if not ok]
    return result


def print_result(spec: dict, r: dict) -> None:
    print("\nWalk-forward choices (each year chosen using only earlier years):")
    for year, sel in r["selections"].items():
        print(f"  {year}: stop = {sel['chosen']:g} x ATR   (training Sharpe by setting: {sel['training_sharpes']})")
    print(f"Full-period Sharpe by setting (plateau check): {r['full_period_sharpe_by_setting']} -> "
          f"{'plateau' if r['plateau_ok'] else 'NOT a plateau'}")
    print(f"Setting that would be frozen if everything passes: stop = {r['final_choice']:g} x ATR")
    print("\nStitched OUT-OF-SAMPLE results (the honest number):")
    S.print_result(spec, r)


# ----------------------------------------------------------------------------- validation
def build_midcap_data() -> None:
    """Current S&P 400 members (minus anything ever in the S&P 500) with daily bars."""
    from .daily import alpaca_headers, bar_cutoff
    response = bx.http_get(MIDCAP_LIST_URL, headers={"User-Agent": bx.settings_value("SEC_USER_AGENT") or "research"})
    try:
        tables = pd.read_html(io.StringIO(response.text))
    except ImportError:
        raise SystemExit("Reading the S&P 400 list needs lxml. Run: pip install lxml   then retry.")
    table = next(t for t in tables if any(str(c).lower() in ("symbol", "ticker symbol") for c in t.columns))
    column = next(c for c in table.columns if str(c).lower() in ("symbol", "ticker symbol"))
    sp500 = set(pd.read_csv(DATA / "universe.csv").symbol.astype(str))
    symbols = sorted({bx.normalize_symbol(s) for s in table[column].astype(str)} - sp500)
    log(f"S&P 400: {len(table)} current members, {len(symbols)} never in the S&P 500 (used for validation)")
    headers, end = alpaca_headers(), bar_cutoff().strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = []
    for i in range(0, max(len(symbols), 1), 100):
        batch = (symbols[i:i + 100] + (["SPY"] if i == 0 else []))
        try:
            parts.append(bx.fetch_bars(batch, "2016-01-01", end, "sip", "all", headers))
        except bx.requests.HTTPError:
            for symbol in batch:
                try:
                    parts.append(bx.fetch_bars([symbol], "2016-01-01", end, "sip", "all", headers))
                except bx.requests.HTTPError:
                    log(f"  Alpaca rejected {symbol}; skipped")
        log(f"  bars: {min(i + 100, len(symbols))}/{len(symbols)}")
    bars = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True)
    MIDCAP.mkdir(parents=True, exist_ok=True)
    bars.to_parquet(MIDCAP / "bars.parquet", index=False)
    pd.DataFrame({"symbol": symbols, "effective_from": "2016-01-01", "effective_to": "2100-01-01",
                  "sector": "Unknown", "cik": None}).to_csv(MIDCAP / "universe.csv", index=False)
    log(f"Mid-cap validation data: {bars.symbol.nunique()} symbols, {bars.timestamp.min():%Y-%m-%d} to "
        f"{bars.timestamp.max():%Y-%m-%d}. Note: today's members only, so delisted mid-caps are missing "
        "(this flatters results; the forward test is still required).")


def validate(hypothesis_id: str) -> None:
    spec = registry.registered_spec(hypothesis_id)
    events = registry.events(hypothesis_id)
    tests = [e for e in events if e["event"] == "tested"]
    if not tests or not tests[-1]["passed"]:
        raise SystemExit("Validation is only for a calibration that passed its walk-forward test.")
    if any(e["event"] == "validated" for e in events):
        raise SystemExit("Already validated once. The validation set is used exactly one time.")
    if not (MIDCAP / "bars.parquet").exists():
        raise SystemExit("Mid-cap data missing. Run: python -m research_kit build-validation-data")
    k = selected_setting(spec)
    data = S.load_stocks(MIDCAP)
    v = spec["validation"]
    base = S.breakout_stops(with_setting(spec, k), float(spec["cost_bps"]), data)
    stress = S.breakout_stops(with_setting(spec, k), float(v["stress_cost_bps"]), data)
    net, spy = S.window(base["ledger"].net, spec), S.window(base["benchmarks"]["SPY"], spec)
    t = S.trade_stats(base["trades"])
    m, ms = S.perf(net), S.perf(S.window(stress["ledger"].net, spec))
    checks = {"positive_net_return": m.get("total_return", -1) > 0,
              f"positive_net_at_{v['stress_cost_bps']:g}_bps": ms.get("total_return", -1) > 0,
              "profit_factor": t.get("profit_factor", 0) >= v["min_profit_factor"],
              "minimum_trades": t.get("trades", 0) >= v["min_trades"]}
    passed = all(checks.values())
    print(f"\nValidation of {hypothesis_id} on mid-caps (stop = {k:g} x ATR, never used in calibration):")
    print(f"  Strategy : CAGR {m['cagr']:+.2%}, Sharpe {m['sharpe']:.2f}, max DD {m['max_drawdown']:.1%}")
    print(f"  SPY      : CAGR {S.perf(spy)['cagr']:+.2%}, Sharpe {S.perf(spy)['sharpe']:.2f}")
    if t.get("trades"):
        print(f"  Trades   : {t['trades']}, win rate {t['win_rate']:.0%}, average win {t['average_win']:+.2%}, "
              f"average loss {t['average_loss']:+.2%}, profit factor {t['profit_factor']:.2f}")
    for key, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key}")
    print("VALIDATED - eligible to freeze for forward testing." if passed else "NOT VALIDATED - close this hypothesis.")
    registry.append({"event": "validated", "id": hypothesis_id, "passed": passed, "setting": k, "checks": checks,
                     "metrics": m, "trades": t, "timestamp": registry.now(), "git_commit": registry.git_commit()})


S.ENGINES["breakout_walkforward"] = engine
