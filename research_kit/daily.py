"""Daily after-close pipeline: incremental data update, health checks, shadow recording,
and evaluation against fixed rules. Designed to run unattended once per weekday.

    python -m research_kit daily

Exit codes (for your own automation):  0 = ok / nothing to do,  1 = failed or data unhealthy
(nothing recorded),  2 = ok and a strategy reached a FINAL verdict today (worth a look).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, time as clock, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import build_expanded_dataset as bx

from . import DATA, RESEARCH, registry, shadow

STATE = RESEARCH / "shadow" / "daily_state.json"
LOCK = RESEARCH / "shadow" / "daily.lock"
MIN_SYMBOLS = 100  # must match how the expanded panel was built (build_expanded_dataset.py default)
SUMMARY = RESEARCH / "shadow" / "daily_summary.csv"
STATUS = RESEARCH / "shadow" / "status.json"
INDEX_URL = "https://www.sec.gov/Archives/edgar/daily-index/{y}/QTR{q}/master.{d}.idx"
PERIODIC_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A", "10-KT", "10-QT", "20-F", "40-F"}
log = shadow.log


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


EASTERN = ZoneInfo("America/New_York")


def bar_cutoff(now: datetime | None = None) -> datetime:
    """Latest moment whose daily bar is final. Before 16:30 New York time on a weekday,
    today's bar is still forming, so it is excluded; afterwards it is included."""
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(EASTERN)
    if local.weekday() < 5 and local.time() < clock(16, 30):
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return (midnight - timedelta(seconds=1)).astimezone(timezone.utc)
    return now - timedelta(minutes=16)


def builder_args(**extra) -> argparse.Namespace:
    values = {"start": "2018-01-01", "end": bar_cutoff().strftime("%Y-%m-%dT%H:%M:%SZ"),
              "feed": "sip", "min_symbols": MIN_SYMBOLS, "refresh_days": None}
    values.update(extra)
    return argparse.Namespace(**values)


# ----------------------------------------------------------------------------- bars
def alpaca_headers() -> dict:
    key = bx.settings_value("APCA_API_KEY_ID", "ALPACA_API_KEY")
    secret = bx.settings_value("APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY")
    if not key or not secret:
        raise SystemExit("Alpaca keys not found in .env")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def fetch_both(symbols: list[str], start: str, end: str, feed: str, headers: dict) -> pd.DataFrame:
    """Adjusted bars plus raw close, retrying one symbol at a time if a batch is rejected."""
    def pair(batch: list[str]) -> pd.DataFrame:
        adjusted = bx.fetch_bars(batch, start, end, feed, "all", headers)
        raw = bx.fetch_bars(batch, start, end, feed, "raw", headers)
        if adjusted.empty:
            return adjusted
        if raw.empty:
            return adjusted.assign(close_raw=np.nan)
        return adjusted.merge(raw[["timestamp", "symbol", "close"]].rename(columns={"close": "close_raw"}),
                              on=["timestamp", "symbol"], how="left")
    parts = []
    for i in range(0, len(symbols), 100):
        batch = symbols[i:i + 100]
        try:
            parts.append(pair(batch))
        except bx.requests.HTTPError as error:
            if error.response is None or error.response.status_code != 400:
                raise
            for symbol in batch:
                try:
                    parts.append(pair([symbol]))
                except bx.requests.HTTPError:
                    log(f"  Alpaca rejected symbol {symbol}; skipped")
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame(columns=["timestamp", "symbol", "open", "high", "low", "close", "volume", "close_raw"])
    frame = pd.concat(parts, ignore_index=True)
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    return frame


def update_bars(args: argparse.Namespace, state: dict) -> pd.Timestamp:
    path = DATA / "bars.parquet"
    bars = pd.read_parquet(path)
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True)
    universe = pd.read_csv(DATA / "universe.csv")
    symbols = sorted(set(universe.symbol.astype(str)) | {"SPY"})
    headers = alpaca_headers()
    last = bars.timestamp.max()
    start = (last - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    log(f"Bars: fetching {start} to now for {len(symbols)} symbols...")
    recent = fetch_both(symbols, start, args.end, args.feed, headers)
    # A split or dividend rewrites a stock's adjusted history: detect it on the overlap days
    # and re-download that stock's full history so returns stay consistent.
    overlap = recent.merge(bars[["timestamp", "symbol", "close"]], on=["timestamp", "symbol"], suffixes=("", "_old"))
    # The last stored day may have been captured before it was final; differences there are
    # not corporate actions, so only earlier overlap days are compared.
    overlap = overlap[overlap.timestamp < last]
    changed = sorted(overlap.loc[(overlap.close / overlap.close_old - 1).abs() > 1e-4, "symbol"].unique())
    missing = sorted(set(symbols) - set(bars.symbol) - set(state.get("no_data_symbols", [])))
    full_start = (pd.Timestamp(args.start) - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
    full = pd.DataFrame()
    if changed or missing:
        log(f"  Re-downloading full history for {len(changed)} adjusted and {len(missing)} new symbols")
        full = fetch_both(changed + missing, full_start, args.end, args.feed, headers)
    refreshed = set(recent.symbol)
    keep = bars[~bars.symbol.isin(changed)
                & ((bars.timestamp < pd.Timestamp(start, tz="UTC")) | ~bars.symbol.isin(refreshed))]
    pieces = [frame for frame in (keep, recent[~recent.symbol.isin(changed)], full) if not frame.empty]
    result = pd.concat(pieces, ignore_index=True)
    for column in ("open", "high", "low", "close", "volume", "close_raw"):
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    result.to_parquet(path, index=False)
    if missing:  # remember symbols Alpaca has no data for, so they are not re-requested daily
        state["no_data_symbols"] = sorted(set(state.get("no_data_symbols", [])) | (set(missing) - set(result.symbol)))
    latest = result.timestamp.max()
    on_latest = result[result.timestamp == latest].symbol.nunique()
    log(f"  Bars through {latest:%Y-%m-%d}: {on_latest} symbols on the latest day")
    return latest


# ----------------------------------------------------------------------------- SEC
def changed_ciks(state: dict, ciks: set[str]) -> tuple[set[str], str]:
    """CIKs in the universe with new periodic reports, from the EDGAR daily index files.
    Indexes are published in the evening, so today's filings are picked up tomorrow."""
    headers = bx.sec_headers()
    default = DATA / "fundamentals.parquet"
    start_from = (datetime.fromtimestamp(default.stat().st_mtime) - timedelta(days=2)).strftime("%Y-%m-%d") \
        if default.exists() else (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    last_done = pd.Timestamp(state.get("last_index_date", start_from))
    today = pd.Timestamp(datetime.now().date())
    found, processed = set(), last_done
    day = last_done + pd.Timedelta(days=1)
    while day < today:
        if day.weekday() < 5:
            url = INDEX_URL.format(y=day.year, q=(day.month - 1) // 3 + 1, d=day.strftime("%Y%m%d"))
            response = bx.http_get(url, headers=headers, pause=0.15)
            if response.ok:
                for line in response.text.splitlines():
                    parts = line.split("|")
                    if len(parts) == 5 and parts[2].strip() in PERIODIC_FORMS:
                        cik = parts[0].strip().zfill(10)
                        if cik in ciks:
                            found.add(cik)
            elif (today - day).days <= 2:
                break  # not published yet; try again tomorrow without skipping it
        processed = day
        day += pd.Timedelta(days=1)
    return found, processed.strftime("%Y-%m-%d")


def refresh_companies(ciks: set[str]) -> None:
    from . import events
    headers = bx.sec_headers()
    for n, cik in enumerate(sorted(ciks), 1):
        response = bx.http_get(bx.SEC_FACTS_URL.format(cik=cik), headers=headers, pause=0.12)
        if not response.ok:
            log(f"  SEC company facts unavailable for {cik} ({response.status_code}); will retry next run")
            continue
        company = response.json()
        fundamentals = bx.company_fundamentals(company)
        if fundamentals.empty:
            fundamentals = pd.DataFrame({"available_at": pd.Series(dtype="datetime64[ns, UTC]")})
        fundamentals.to_parquet(DATA / "fundamentals_cache" / f"{cik}.parquet", index=False)
        sue = events.sue_events(company)
        if sue.empty:
            sue = pd.DataFrame({"available_at": pd.Series(dtype="datetime64[ns, UTC]"),
                                "sue": pd.Series(dtype=float), "period_end": pd.Series(dtype="datetime64[ns]")})
        sue.to_parquet(DATA / "eps_cache" / f"{cik}.parquet", index=False)
    log(f"  Updated fundamentals and earnings for {len(ciks)} companies with new filings")


# ----------------------------------------------------------------------------- checks
def health(panel: pd.DataFrame, latest_bar: pd.Timestamp) -> list[str]:
    if panel.empty:
        return ["the rebuilt panel is empty"]
    problems = []
    latest = panel.timestamp.max()
    if latest < latest_bar:
        problems.append(f"panel ends {latest:%Y-%m-%d} but bars reach {latest_bar:%Y-%m-%d}")
    counts = panel.groupby("timestamp").symbol.nunique()
    recent_median = counts.iloc[-21:-1].median() if len(counts) > 21 else counts.median()
    if counts.iloc[-1] < 0.95 * recent_median:
        problems.append(f"only {counts.iloc[-1]} stocks on {latest:%Y-%m-%d} vs about {recent_median:.0f} normally")
    age = (pd.Timestamp.now(tz="UTC") - latest).days
    if age > 5:
        problems.append(f"latest data is {age} days old")
    return problems


# ----------------------------------------------------------------------------- main
def run_daily(force: bool = False, min_symbols: int | None = None) -> int:
    global MIN_SYMBOLS
    if min_symbols:
        MIN_SYMBOLS = min_symbols
    from . import events
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 6 * 3600:
        log("Another daily run is in progress (lock file present); exiting.")
        return 0
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    state = load_state()
    try:
        if not shadow.frozen_strategies():
            log("No frozen strategies yet; nothing to forward-test. Freeze one first.")
            return 0
        args = builder_args()
        if bar_cutoff() < datetime.now(timezone.utc) - timedelta(hours=1):
            log("Market session not finished yet (before 16:30 New York time): today's bar is excluded.")
        universe_path = DATA / "universe.csv"
        if time.time() - universe_path.stat().st_mtime > 7 * 86400:
            log("Weekly universe refresh...")
            bx.step_universe(args)
            state.pop("no_data_symbols", None)  # give renamed or new symbols another chance
        latest_bar = update_bars(args, state)
        if any(f["spec"].get("strategy_type") == "etf_trend" for f in shadow.frozen_strategies()):
            from .strategies import build_etf_data
            log("ETF bars: refreshing...")
            build_etf_data()
        if not force and str(latest_bar) == state.get("last_bar_date"):
            log(f"No new trading day since {latest_bar:%Y-%m-%d} (weekend or holiday); evaluation only.")
        else:
            universe = pd.read_csv(universe_path, dtype={"cik": str})
            ciks = set(universe.cik.dropna().str.zfill(10))
            found, processed = changed_ciks(state, ciks)
            if found:
                refresh_companies(found)
            state["last_index_date"] = processed
            log("Rebuilding fundamentals, earnings and panel...")
            bx.step_fundamentals(args)            # cached companies: concatenation only
            events.build_sue(refresh_days=None)   # cached companies: concatenation only
            events.build_insiders(start="2018-01-01")
            bx.step_panel(args)
            events.build_panel_v2()
            panel = pd.read_parquet(DATA / "model_panel_v2.parquet")
            panel["timestamp"] = pd.to_datetime(panel.timestamp, utc=True)
            problems = health(panel, latest_bar)
            if problems:
                for problem in problems:
                    log(f"DATA UNHEALTHY: {problem}")
                log("Nothing recorded today. Fix the data issue; the next run will catch up.")
                write_status(state, [], problems)
                return 1
            shadow.run(skip_refresh=True)
            state["last_bar_date"] = str(latest_bar)
        results = [shadow.evaluate(frozen) for frozen in shadow.frozen_strategies()]
        for result in results:
            log(shadow.describe(result))
        append_summary(results)
        write_status(state, results, [])
        state["last_success"] = registry.now()
        save_state(state)
        if any(r.get("new_verdict") for r in results):
            log("A strategy reached a FINAL verdict today - see research/shadow/status.json")
            return 2
        return 0
    except SystemExit as error:
        log(f"FAILED: {error}")
        return 1
    except Exception as error:  # keep unattended runs from dying silently
        log(f"FAILED: {type(error).__name__}: {error}")
        return 1
    finally:
        LOCK.unlink(missing_ok=True)


def append_summary(results: list[dict]) -> None:
    rows = [{"date": datetime.now().strftime("%Y-%m-%d"), "id": r["id"], "verdict": r["verdict"],
             "completed": r["completed"], "needed": r["needed"], "net_return": r.get("net_return"),
             "sharpe": r.get("sharpe"), "max_drawdown": r.get("max_drawdown"),
             "t_vs_backtest": r.get("t_vs_backtest"),
             "open_unrealized": (r.get("open_period") or {}).get("unrealized_gross")} for r in results]
    frame = pd.DataFrame(rows)
    frame.to_csv(SUMMARY, mode="a", header=not SUMMARY.exists(), index=False)


def write_status(state: dict, results: list[dict], problems: list[str]) -> None:
    STATUS.write_text(json.dumps({"updated": registry.now(), "healthy": not problems, "problems": problems,
                                  "last_bar_date": state.get("last_bar_date"),
                                  "strategies": results}, indent=2, default=str), encoding="utf-8")
