"""Rule-based strategies with no model fitting. Every rule and number is fixed in the
hypothesis spec, so once a strategy is frozen, its results on data after the freeze date
are a genuine forward test.

  etf_trend          Cross-asset trend following with ETFs (monthly, long-only).
  longonly_momentum  Hold S&P 500 stocks with the strongest 12-month gains (monthly).
  breakout_stops     Buy fresh breakouts after big quick gains; sell on a tight stop,
                     a trailing stop, or after a maximum holding period (daily).

Conventions that keep the tests honest:
  - Decisions use closes up to day d only; trades happen the NEXT trading day
    (monthly strategies at that day's close, breakouts at that day's open).
  - Stops: a gap below the stop exits at the open, not at the stop price.
  - Costs are charged on every trade, and every result is repeated at higher costs.
  - Stocks are eligible only on days they were actually in the S&P 500.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import build_expanded_dataset as bx

from . import DATA, RESEARCH, registry

ETF_BARS = DATA.parent / "etf" / "bars.parquet"
ETF_UNIVERSE = ["SPY", "EFA", "EEM", "IWM", "VNQ", "TLT", "IEF", "AGG", "GLD", "DBC", "BIL"]
YEAR = 252


def log(message: str) -> None:
    print(message, flush=True)


# ============================================================================ data
def build_etf_data(start: str = "2015-01-01") -> pd.DataFrame:
    """Full adjusted (dividend-inclusive) daily history for the ETF universe. Re-downloaded
    in full each time: it is small, and this keeps dividend adjustments consistent."""
    from .daily import alpaca_headers, bar_cutoff
    headers = alpaca_headers()
    end = bar_cutoff().strftime("%Y-%m-%dT%H:%M:%SZ")
    frames = []
    for feed in ("sip", "iex"):
        try:
            frames = [bx.fetch_bars(ETF_UNIVERSE, start, end, feed, "all", headers)]
            break
        except SystemExit:
            if feed == "iex":
                raise
            log("  Full-market feed refused for ETFs; using IEX.")
    frame = frames[0]
    if frame.empty:
        raise SystemExit("Alpaca returned no ETF bars.")
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    frame = frame.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"])
    ETF_BARS.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(ETF_BARS, index=False)
    missing = sorted(set(ETF_UNIVERSE) - set(frame.symbol))
    log(f"ETF bars: {frame.symbol.nunique()} ETFs, {frame.timestamp.min():%Y-%m-%d} to "
        f"{frame.timestamp.max():%Y-%m-%d}" + (f"; missing: {', '.join(missing)}" if missing else ""))
    return frame


def _matrix(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return frame.pivot_table(index="timestamp", columns="symbol", values=column).sort_index()


def load_etf_closes(symbols: list[str]) -> pd.DataFrame:
    if not ETF_BARS.exists():
        raise SystemExit("ETF data missing. Run: python -m research_kit build-strategy-data")
    bars = pd.read_parquet(ETF_BARS)
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True)
    closes = _matrix(bars, "close")
    missing = [s for s in symbols if s not in closes.columns]
    if missing:
        raise SystemExit(f"ETF data has no history for {missing}. Run: python -m research_kit build-strategy-data")
    return closes[symbols]


def load_stocks(directory=None) -> dict:
    """Adjusted stock bars plus a point-in-time membership matrix (S&P 500 by default)."""
    directory = directory or DATA
    bars = pd.read_parquet(directory / "bars.parquet")
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True)
    universe = pd.read_csv(directory / "universe.csv")
    data = {c: _matrix(bars, c) for c in ("open", "high", "low", "close", "volume")}
    dates, symbols = data["close"].index, data["close"].columns
    member = pd.DataFrame(False, index=dates, columns=symbols)
    for row in universe.itertuples():
        if row.symbol in member.columns:
            start = pd.Timestamp(row.effective_from, tz="UTC") if pd.Timestamp(row.effective_from).tzinfo is None \
                else pd.Timestamp(row.effective_from)
            end = pd.Timestamp(row.effective_to)
            end = end.tz_localize("UTC") if end.tzinfo is None else end
            member.loc[(dates >= start) & (dates <= end), row.symbol] = True
    data["member"] = member
    return data


def latest_date(spec: dict) -> pd.Timestamp:
    if spec["strategy_type"] == "etf_trend":
        return load_etf_closes([spec["cash"]]).index.max()
    bars = pd.read_parquet(DATA / "bars.parquet", columns=["timestamp"])
    return pd.to_datetime(bars.timestamp, utc=True).max()


# ============================================================================ engines
def month_ends(dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    series = pd.Series(dates, index=dates)
    return list(series.groupby([dates.year, dates.month]).max())


def run_weights(closes: pd.DataFrame, targets: dict, cost_bps: float) -> tuple[pd.DataFrame, pd.Series]:
    """Holdings drift with prices between rebalances. A target decided at close d is
    traded at the close of the next trading day. Uninvested weight is cash at 0%."""
    returns = closes.pct_change(fill_method=None)
    dates = closes.index
    schedule = {}
    for decided, weights in targets.items():
        i = dates.get_loc(decided)
        if i + 1 < len(dates):
            schedule[dates[i + 1]] = weights
    position = pd.Series(0.0, index=closes.columns)
    rows = []
    for day in dates:
        r = returns.loc[day].fillna(0.0)  # missing price (e.g. delisted): treated as unchanged
        gross = float((position * r).sum())
        position = position * (1 + r) / (1 + gross) if gross > -1 else position * 0
        turnover = 0.0
        if day in schedule:
            target = schedule[day].reindex(position.index).fillna(0.0)
            turnover = float((target - position).abs().sum())
            position = target
        net = (1 + gross) * (1 - turnover * cost_bps / 1e4) - 1
        rows.append((day, gross, net, turnover))
    ledger = pd.DataFrame(rows, columns=["timestamp", "gross", "net", "turnover"]).set_index("timestamp")
    return ledger, position[position.abs() > 1e-9]


def etf_trend(spec: dict, cost_bps: float) -> dict:
    rule, assets, cash = spec["rule"], spec["assets"], spec["cash"]
    bench = spec["benchmark"]["weights"]
    closes = load_etf_closes(sorted(set(assets) | {cash} | set(bench)))
    lookback = int(rule["lookback_days"])
    targets, bench_targets = {}, {}
    for decided in month_ends(closes.index):
        i = closes.index.get_loc(decided)
        if i < lookback:
            continue
        momentum = closes.iloc[i] / closes.iloc[i - lookback] - 1
        live = [a for a in assets if np.isfinite(momentum.get(a, np.nan))]
        if not live or not np.isfinite(momentum[cash]):
            continue
        weights = pd.Series(0.0, index=closes.columns)
        for asset in live:  # each asset gets an equal slot: the asset if it beats cash, else cash
            weights[asset if momentum[asset] > momentum[cash] else cash] += 1.0 / len(live)
        targets[decided] = weights
        bench_targets[decided] = pd.Series(bench, dtype=float)
    ledger, holdings = run_weights(closes, targets, cost_bps)
    benchmark, _ = run_weights(closes, bench_targets, cost_bps)
    start = closes.index[closes.index.get_loc(min(targets)) + 1] if targets else closes.index[-1]
    return {"ledger": ledger[ledger.index >= start], "benchmarks": {"60/40": benchmark.net[benchmark.index >= start]},
            "holdings": holdings, "stats": {"rebalances": len(targets)}}


def longonly_momentum(spec: dict, cost_bps: float, data: dict | None = None) -> dict:
    rule = spec["rule"]
    data = data or load_stocks()
    closes, member = data["close"], data["member"]
    long_lb, skip = int(rule["lookback_days"]), int(rule["skip_days"])
    top, keep = float(rule["top_fraction"]), float(rule["keep_fraction"])
    targets, equal_targets, holding = {}, {}, set()
    for decided in month_ends(closes.index):
        i = closes.index.get_loc(decided)
        if i < long_lb:
            continue
        momentum = closes.iloc[i - skip] / closes.iloc[i - long_lb] - 1
        eligible = momentum[member.iloc[i] & momentum.notna() & closes.iloc[i].notna()]
        if len(eligible) < 50:
            continue
        pct = eligible.rank(pct=True)
        chosen = set(pct[pct > 1 - top].index) | {s for s in holding if s in pct and pct[s] > 1 - keep}
        holding = chosen
        targets[decided] = pd.Series(1.0 / len(chosen), index=sorted(chosen))
        equal_targets[decided] = pd.Series(1.0 / len(eligible), index=eligible.index)
    ledger, holdings = run_weights(closes, targets, cost_bps)
    equal, _ = run_weights(closes, equal_targets, cost_bps)
    spy, _ = run_weights(closes[["SPY"]], {d: pd.Series({"SPY": 1.0}) for d in targets}, cost_bps)
    start = closes.index[closes.index.get_loc(min(targets)) + 1] if targets else closes.index[-1]
    keep_after = lambda s: s[s.index >= start]
    return {"ledger": keep_after(ledger), "holdings": holdings,
            "benchmarks": {"SPY": keep_after(spy.net), "equal_weight_universe": keep_after(equal.net)},
            "stats": {"rebalances": len(targets), "average_holdings": float(np.mean([len(t) for t in targets.values()]))
                      if targets else 0.0}}


def breakout_stops(spec: dict, cost_bps: float, data: dict | None = None) -> dict:
    rule = spec["rule"]
    data = data or load_stocks()
    o, h, low, c, v, member = (data[k] for k in ("open", "high", "low", "close", "volume", "member"))
    dates = c.index
    gain = c / c.shift(int(rule["gain_days"])) - 1
    at_high = c >= c.rolling(int(rule["high_days"]), min_periods=int(rule["high_days"])).max()
    volume_ok = v >= float(rule["volume_multiple"]) * v.shift(1).rolling(20, min_periods=15).mean()
    signal = (gain >= float(rule["min_gain"])) & at_high & volume_ok & member
    cost = cost_bps / 1e4
    atr_mode = "stop_atr" in rule
    if atr_mode:  # stops sized to each stock's own volatility, position sized from the stop
        prev = c.shift(1)
        true_range = pd.concat([h - low, (h - prev).abs(), (low - prev).abs()]).groupby(level=0).max()
        atr = true_range.rolling(14, min_periods=14).mean()
        signal &= atr.notna()
        stop_k, trail_k = float(rule["stop_atr"]), float(rule["trail_atr"])
        risk, cap = float(rule["risk_per_trade"]), float(rule["max_position"])
    else:
        stop_loss, trail = float(rule["stop_loss"]), float(rule["trailing_stop"])
        size = float(rule["position_size"])
    max_hold = int(rule["max_hold_days"])
    max_positions, max_new = int(rule["max_positions"]), int(rule["max_new_per_day"])
    cash, positions, trades, equity_rows, pending = 1.0, {}, [], [], []
    for i, day in enumerate(dates):
        # 1) buy yesterday's signals at today's open
        for symbol, budget, vol in pending:
            price = o.at[day, symbol]
            if symbol in positions or not np.isfinite(price) or price <= 0 or budget > cash:
                continue
            shares = budget * (1 - cost) / price
            cash -= budget
            positions[symbol] = {"shares": shares, "entry": price, "entry_date": day, "peak": price, "days": 0,
                                 "stop_dist": stop_k * vol if atr_mode else price * stop_loss,
                                 "trail_dist": trail_k * vol if atr_mode else None}
        pending = []
        # 2) manage open positions
        for symbol in list(positions):
            p = positions[symbol]
            open_, low_, close_ = o.at[day, symbol], low.at[day, symbol], c.at[day, symbol]
            hard = p["entry"] - p["stop_dist"]
            trail_level = p["peak"] - p["trail_dist"] if atr_mode else p["peak"] * (1 - trail)
            exit_price, reason = None, None
            if not np.isfinite(close_):  # no data (delisted): exit at last known close
                exit_price, reason = p.get("last", p["entry"]), "no_data"
            elif p["days"] > 0 and np.isfinite(open_) and open_ <= hard:
                exit_price, reason = open_, "stop_gap"
            elif np.isfinite(low_) and low_ <= hard:
                exit_price, reason = hard, "stop"
            elif p["days"] > 0 and close_ <= trail_level:
                exit_price, reason = close_, "trailing"
            elif p["days"] + 1 >= max_hold:
                exit_price, reason = close_, "max_hold"
            if exit_price is not None:
                proceeds = p["shares"] * exit_price * (1 - cost)
                cash += proceeds
                trades.append({"symbol": symbol, "entry_date": p["entry_date"], "exit_date": day,
                               "entry": p["entry"], "exit": exit_price, "reason": reason, "days": p["days"] + 1,
                               "return": exit_price * (1 - cost) / (p["entry"] / (1 - cost)) - 1})
                del positions[symbol]
            else:
                p["peak"], p["last"], p["days"] = max(p["peak"], close_), close_, p["days"] + 1
        equity = cash + sum(p["shares"] * p.get("last", p["entry"]) for p in positions.values())
        equity_rows.append((day, equity))
        # 3) today's signals, ranked by size of the gain, for tomorrow's open
        free = max_positions - len(positions)
        if free > 0 and i + 1 < len(dates):
            row = signal.iloc[i]
            candidates = gain.iloc[i][row[row].index].drop(labels=list(positions), errors="ignore")
            for symbol in candidates.sort_values(ascending=False).index[: min(free, max_new)]:
                if atr_mode:
                    vol, price = atr.iat[i, atr.columns.get_loc(symbol)], c.iat[i, c.columns.get_loc(symbol)]
                    budget = min(cap * equity, risk * equity * price / (stop_k * vol))
                    pending.append((symbol, budget, vol))
                else:
                    pending.append((symbol, size * equity, None))
    curve = pd.Series(dict(equity_rows)).sort_index()
    net = curve.pct_change().fillna(0.0)
    ledger = pd.DataFrame({"gross": net, "net": net, "turnover": np.nan})
    spy = c["SPY"].pct_change(fill_method=None).fillna(0.0) if "SPY" in c else net * 0
    open_positions = pd.Series({s: p["shares"] * p.get("last", p["entry"]) / curve.iloc[-1]
                                for s, p in positions.items()}, dtype=float)
    return {"ledger": ledger, "benchmarks": {"SPY": spy}, "holdings": open_positions,
            "trades": pd.DataFrame(trades), "stats": {}}


ENGINES = {"etf_trend": etf_trend, "longonly_momentum": longonly_momentum, "breakout_stops": breakout_stops}


# ============================================================================ metrics
def perf(daily: pd.Series) -> dict:
    daily = daily.dropna()
    if len(daily) < 2:
        return {"days": len(daily)}
    curve = (1 + daily).cumprod()
    years = len(daily) / YEAR
    monthly = (1 + daily).groupby([daily.index.year, daily.index.month]).prod() - 1
    sd = float(daily.std(ddof=1))
    return {"days": len(daily), "months": len(monthly), "total_return": float(curve.iloc[-1] - 1),
            "cagr": float(curve.iloc[-1] ** (1 / years) - 1) if years > 0 else 0.0,
            "volatility": sd * np.sqrt(YEAR), "sharpe": float(daily.mean() / sd * np.sqrt(YEAR)) if sd > 0 else 0.0,
            "max_drawdown": float((curve / curve.cummax() - 1).min()), "worst_month": float(monthly.min())}


def month_of(index: pd.DatetimeIndex) -> pd.PeriodIndex:
    return (index.tz_convert(None) if index.tz is not None else index).to_period("M")


def monthly(daily: pd.Series) -> pd.Series:
    out = (1 + daily).groupby([daily.index.year, daily.index.month]).prod() - 1
    out.index = [f"{y}-{m:02d}" for y, m in out.index]
    return out


def excess_t(strategy: pd.Series, benchmark: pd.Series) -> float:
    diff = (monthly(strategy) - monthly(benchmark.reindex(strategy.index).fillna(0.0))).dropna()
    sd = diff.std(ddof=1)
    return float(diff.mean() / sd * np.sqrt(len(diff))) if len(diff) > 2 and sd > 0 else 0.0


def trade_stats(trades: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {"trades": 0}
    r = trades["return"]
    wins, losses = r[r > 0], r[r <= 0]
    return {"trades": len(r), "win_rate": float((r > 0).mean()), "average_win": float(wins.mean()) if len(wins) else 0.0,
            "average_loss": float(losses.mean()) if len(losses) else 0.0,
            "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf"),
            "average_days_held": float(trades.days.mean()),
            "exit_reasons": trades.reason.value_counts(normalize=True).round(3).to_dict(),
            "worst_trade": float(r.min()), "best_trade": float(r.max())}


# ============================================================================ historical test
def window(series: pd.Series, spec: dict) -> pd.Series:
    start = pd.Timestamp(spec["window"]["start"], tz="UTC")
    end = pd.Timestamp(spec["window"]["end"], tz="UTC")
    return series[(series.index >= start) & (series.index <= end)]


def run_test(spec: dict) -> dict:
    kind = spec["strategy_type"]
    engine = ENGINES[kind]
    data = None if kind == "etf_trend" else load_stocks()
    call = (lambda bps: engine(spec, bps)) if data is None else (lambda bps: engine(spec, bps, data))
    base = call(float(spec["cost_bps"]))
    net = window(base["ledger"].net, spec)
    result = {"strategy_type": kind, "metrics": perf(net), "stats": base["stats"],
              "benchmarks": {name: perf(window(series, spec)) for name, series in base["benchmarks"].items()},
              "excess_t_vs": {name: excess_t(net, window(series, spec)) for name, series in base["benchmarks"].items()},
              "yearly": {str(y): float(v) for y, v in ((1 + net).groupby(net.index.year).prod() - 1).items()},
              "cost_sensitivity": {}, "ic_checks": {}}
    if "trades" in base:
        trades = base["trades"]
        if not trades.empty:
            trades = trades[(trades.entry_date >= net.index.min()) & (trades.exit_date <= net.index.max())]
        result["trades"] = trade_stats(trades)
    for bps in spec.get("sensitivity_costs", []):
        alt = window(call(float(bps))["ledger"].net, spec)
        result["cost_sensitivity"][f"{bps:g}"] = perf(alt)
    result["checks"] = gates(spec, result)
    result["passed"] = all(result["checks"].values())
    result["blocking"] = [k for k, ok in result["checks"].items() if not ok]
    return result


def gates(spec: dict, r: dict) -> dict:
    g, m, kind = spec["gates"], r["metrics"], spec["strategy_type"]
    worst_bps = f"{max(spec.get('sensitivity_costs', [spec['cost_bps']])):g}"
    stressed = r["cost_sensitivity"].get(worst_bps, m)
    checks = {"minimum_months": m.get("months", 0) >= g["min_months"],
              "positive_net_return": m.get("total_return", -1) > 0,
              f"positive_net_at_{worst_bps}_bps": stressed.get("total_return", -1) > 0}
    if kind == "etf_trend":
        b = r["benchmarks"]["60/40"]
        checks["sharpe_at_least_ratio_of_6040"] = m["sharpe"] >= g["min_sharpe_ratio_vs_benchmark"] * b["sharpe"]
        checks["drawdown_shallower_than_6040"] = m["max_drawdown"] >= b["max_drawdown"]
    elif kind == "longonly_momentum":
        for name in ("SPY", "equal_weight_universe"):
            checks[f"beats_{name}"] = m["cagr"] > r["benchmarks"][name]["cagr"]
        checks["excess_vs_equal_weight_t_stat"] = r["excess_t_vs"]["equal_weight_universe"] >= g["min_excess_t"]
        checks["drawdown_within_limit_of_spy"] = m["max_drawdown"] >= r["benchmarks"]["SPY"]["max_drawdown"] - g["max_extra_drawdown"]
    else:
        t = r.get("trades", {})
        checks["minimum_trades"] = t.get("trades", 0) >= g["min_trades"]
        checks["profit_factor"] = t.get("profit_factor", 0) >= g["min_profit_factor"]
        checks["sharpe_at_least_spy"] = m["sharpe"] >= r["benchmarks"]["SPY"]["sharpe"]
        checks["maximum_drawdown"] = m["max_drawdown"] >= g["max_drawdown"]
    return checks


def print_result(spec: dict, r: dict) -> None:
    fmt = lambda p: (f"CAGR {p.get('cagr', 0):+.2%}, total {p.get('total_return', 0):+.1%}, Sharpe {p.get('sharpe', 0):.2f}, "
                     f"max DD {p.get('max_drawdown', 0):.1%}, worst month {p.get('worst_month', 0):.1%}")
    if spec.get("related_closed_features"):
        print(f"Note: related feature(s) already examined on this data: {spec['related_closed_features']}. "
              f"{spec.get('prior_evidence', '')}")
    print(f"\n{spec['id']} ({r['metrics'].get('months', 0)} months)")
    print(f"  Strategy   : {fmt(r['metrics'])}")
    for name, p in r["benchmarks"].items():
        print(f"  {name:11s}: {fmt(p)}   (monthly excess t-stat vs it: {r['excess_t_vs'][name]:+.2f})")
    for bps, p in r["cost_sensitivity"].items():
        print(f"  At {bps} bps : {fmt(p)}")
    if r.get("stats"):
        print(f"  Stats      : {r['stats']}")
    if "trades" in r:
        t = r["trades"]
        if t.get("trades"):
            print(f"  Trades     : {t['trades']}, win rate {t['win_rate']:.0%}, average win {t['average_win']:+.2%}, "
                  f"average loss {t['average_loss']:+.2%}, profit factor {t['profit_factor']:.2f}, "
                  f"held {t['average_days_held']:.1f} days on average")
            print(f"  Exits      : {t['exit_reasons']}; worst trade {t['worst_trade']:+.1%}")
        else:
            print("  Trades     : none")
    print("  Year by year: " + ", ".join(f"{y} {v:+.1%}" for y, v in r["yearly"].items()))
    print("\nGates:")
    for key, ok in r["checks"].items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key}")
    print(f"\nDecision rule (registered in advance): {spec['decision_rule']}")
    print("RESULT: PASSED - eligible to freeze." if r["passed"]
          else f"RESULT: FAILED ({', '.join(r['blocking'])}). Per the decision rule, close this hypothesis.")


# ============================================================================ forward test
def record_snapshot(frozen: dict) -> None:
    """Append today's holdings so the forward record can be audited later."""
    from . import calibration  # noqa: F401  (registers the calibrated engine)
    from .shadow import SHADOW, log as slog
    spec, hid = frozen["spec"], frozen["id"]
    result = ENGINES[spec["strategy_type"]](spec, float(spec["cost_bps"]))
    day = result["ledger"].index.max()
    path = SHADOW / hid / "book.parquet"
    book = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=["timestamp", "symbol", "weight"])
    if not book.empty and pd.Timestamp(book.timestamp.max()) >= day:
        slog(f"{hid}: holdings for {day:%Y-%m-%d} already recorded.")
        return
    holdings = result["holdings"]
    rows = pd.DataFrame({"timestamp": day, "symbol": holdings.index, "weight": holdings.values})
    previous = book[book.timestamp == book.timestamp.max()].set_index("symbol").weight if not book.empty else pd.Series(dtype=float)
    changed = previous.round(6).sort_index().to_dict() != holdings.round(6).sort_index().to_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([book, rows], ignore_index=True).to_parquet(path, index=False)
    if changed:
        registry.append({"event": "shadow_rebalance", "id": hid, "data_date": str(day),
                         "positions": len(holdings), "timestamp": registry.now()})
    slog(f"{hid}: recorded {len(holdings)} holdings for {day:%Y-%m-%d}" + (" (changed)" if changed else ""))


def evaluate_forward(frozen: dict) -> dict:
    from . import calibration  # noqa: F401
    from .shadow import EVALUATION_RULES as rules, _write_report, final_verdict
    spec, hid = frozen["spec"], frozen["id"]
    freeze = pd.Timestamp(frozen["freeze_data_date"])
    freeze = freeze.tz_localize("UTC") if freeze.tzinfo is None else freeze
    result = ENGINES[spec["strategy_type"]](spec, float(spec["cost_bps"]))
    net = result["ledger"].net
    net = net[net.index > freeze]
    bench_name = spec["forward"]["benchmark"]
    bench = result["benchmarks"][bench_name].reindex(net.index).fillna(0.0)
    months = monthly(net) if len(net) else pd.Series(dtype=float)
    complete = months.iloc[:-1] if len(months) else months  # the current month is still open
    needed = int(spec["forward"]["min_periods"])
    out = {"id": hid, "status_class": frozen["status"], "rules": rules, "completed": len(complete), "needed": needed,
           "open_period": {"since": months.index[-1], "days_held": int((month_of(net.index) == month_of(net.index)[-1]).sum()),
                           "unrealized_gross": float(months.iloc[-1])} if len(months) else {},
           "as_of": registry.now(), "benchmark": bench_name}
    historical = RESEARCH / "results" / hid / "result.json"
    hist = json.loads(historical.read_text(encoding="utf-8"))["metrics"] if historical.exists() else {}
    if len(complete) >= 2:
        days = net[month_of(net.index).astype(str).isin(complete.index)]
        p, b = perf(days), perf(bench.reindex(days.index))
        expected = (1 + hist.get("cagr", 0.0)) ** (1 / 12) - 1
        sd = complete.std(ddof=1)
        out.update({"net_return": p["total_return"], "sharpe": p["sharpe"], "max_drawdown": p["max_drawdown"],
                    "benchmark_return": b["total_return"], "benchmark_sharpe": b["sharpe"],
                    "t_stat": float(complete.mean() / sd * np.sqrt(len(complete))) if sd > 0 else 0.0,
                    "t_vs_backtest": float((complete.mean() - expected) / sd * np.sqrt(len(complete))) if sd > 0 else 0.0})
    if "trades" in result and not result["trades"].empty:
        out["trades"] = trade_stats(result["trades"][result["trades"].entry_date > freeze])
    previous = final_verdict(hid)
    if previous:
        out.update({"verdict": previous["outcome"], "final": True,
                    "reason": f"FINAL since {previous['timestamp'][:10]}: {previous['reason']} (figures keep updating)"})
        _write_report(hid, pd.DataFrame({"month": complete.index, "net_return": complete.values}), out)
        return out
    n, outcome, reason = len(complete), None, None
    hist_dd = hist.get("max_drawdown")
    dd_limit = rules["early_retire_drawdown_multiple"] * hist_dd if hist_dd else rules["early_retire_drawdown_floor"]
    if rules["early_retire_after_periods"] <= n < needed:
        if out.get("max_drawdown", 0) < dd_limit:
            outcome, reason = "retired", f"drawdown {out['max_drawdown']:.1%} breached the limit {dd_limit:.1%}"
        elif out.get("t_vs_backtest", 0) < rules["early_retire_t_vs_backtest"]:
            outcome, reason = "retired", f"significantly worse than the backtest (t = {out['t_vs_backtest']:.2f})"
    elif n >= needed:
        beat = (out.get("sharpe", 0) >= out.get("benchmark_sharpe", 0) if spec["forward"].get("compare") == "sharpe"
                else out.get("net_return", 0) > out.get("benchmark_return", 0))
        ok = out.get("net_return", 0) > 0 and beat and out.get("t_vs_backtest", 0) >= rules["final_t_vs_backtest_floor"]
        if ok and frozen["status"] == "qualified":
            outcome, reason = "supported", f"forward results confirm the backtest and beat {bench_name}; ready for human review"
        elif ok:
            outcome, reason = "informative", "forward results look good, but this strategy is exploratory"
        else:
            outcome, reason = "retired", (f"after {n} months: net {out.get('net_return', 0):+.2%} vs {bench_name} "
                                          f"{out.get('benchmark_return', 0):+.2%}, Sharpe {out.get('sharpe', 0):.2f}")
    if outcome:
        registry.append({"event": "verdict", "id": hid, "outcome": outcome, "reason": reason, "completed_periods": n,
                         "metrics_at_verdict": {k: out.get(k) for k in ("net_return", "sharpe", "max_drawdown", "t_vs_backtest")},
                         "rules_version": rules["version"], "timestamp": registry.now()})
        out.update({"verdict": outcome, "reason": reason, "final": True, "new_verdict": True})
    else:
        out.update({"verdict": "collecting", "final": False,
                    "reason": f"{n}/{needed} completed months vs {bench_name}; early retirement possible from month "
                              f"{rules['early_retire_after_periods']}, a positive verdict only at {needed}"})
    _write_report(hid, pd.DataFrame({"month": complete.index, "net_return": complete.values}), out)
    return out
