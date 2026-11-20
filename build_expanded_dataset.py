"""Build an expanded V5.6 research panel: ~500 stocks, 2018 onward, with fundamentals.

Run from the project root with the virtual environment active:
    python build_expanded_dataset.py all          # every step, in order
    python build_expanded_dataset.py universe     # or one step at a time:
    python build_expanded_dataset.py bars         #   universe -> bars -> fundamentals -> panel
    python build_expanded_dataset.py fundamentals
    python build_expanded_dataset.py panel

Steps
  universe      Historical S&P 500 membership (who was in the index on each date,
                including companies later removed), GICS sectors, SEC CIK numbers.
  bars          Daily bars from Alpaca for every member plus SPY, adjusted and raw.
  fundamentals  Point-in-time SEC XBRL fundamentals. Each value is dated by when it
                was FILED with the SEC (+1 day), never by the period it describes.
                Raw SEC files are parsed in memory; only compact results are saved.
  panel         Features, beta, sector, fundamentals and valuation ratios. Each
                feature appears once, cross-sectionally ranked (no raw/rank pairs).

Downloads are cached under data/research/v56-expanded/, so an interrupted run
resumes where it stopped. Add that folder to .gitignore; it is data, not code.

Credentials come from your .env (ALPACA_API_KEY, ALPACA_SECRET_KEY, SEC_USER_AGENT)
or the APCA_API_KEY_ID / APCA_API_SECRET_KEY environment variables. SEC requires
SEC_USER_AGENT to contain a real contact email.

Known limits of free data (be aware when reading results):
  - Some removed companies have no Alpaca bars or no SEC filings under the old
    ticker; the script reports how many. Coverage is good, not perfect.
  - Sectors for removed companies come from SEC industry (SIC) codes mapped to
    GICS-style names, which is close to but not identical to official GICS.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT = Path("data/research/v56-expanded")
HIST_URL = "https://raw.githubusercontent.com/hanshof/sp500_constituents/main/sp_500_historical_components.csv"
CURRENT_URL = "https://raw.githubusercontent.com/hanshof/sp500_constituents/main/sp500_constituents.csv"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ALPACA_URL = "https://data.alpaca.markets/v2/stocks/bars"
FAR_FUTURE = pd.Timestamp("2100-01-01", tz="UTC")

FLOW_TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "net_income": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities",
                            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "gross_profit": ["GrossProfit"],
}
INSTANT_TAGS = {
    "total_assets": ["Assets"],
    "total_equity": ["StockholdersEquity",
                     "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
SHARE_TAGS = [("dei", "EntityCommonStockSharesOutstanding"), ("us-gaap", "CommonStockSharesOutstanding")]


# --------------------------------------------------------------------------- helpers
def log(message: str) -> None:
    print(message, flush=True)


def settings_value(*names: str) -> str:
    """First non-empty value from environment variables or the project's settings."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value and not value.startswith("PASTE_"):
            return value
    try:
        from finai.core.config import get_settings
        settings = get_settings()
        for name in names:
            value = str(getattr(settings, name.lower(), "") or "").strip()
            if value and not value.startswith("PASTE_"):
                return value
    except Exception:
        pass
    return ""


def http_get(url: str, *, headers: dict | None = None, params: dict | None = None,
             retries: int = 5, pause: float = 0.0) -> requests.Response:
    for attempt in range(retries):
        response = requests.get(url, headers=headers, params=params, timeout=90)
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(min(60, 2 ** attempt * 2))
            continue
        if pause:
            time.sleep(pause)
        return response
    response.raise_for_status()
    return response


def sec_headers() -> dict:
    agent = settings_value("SEC_USER_AGENT")
    if "@" not in agent or "example.com" in agent:
        raise SystemExit("Set SEC_USER_AGENT in .env to 'YourName your.real@email.com' (SEC requires it).")
    return {"User-Agent": agent, "Accept-Encoding": "gzip, deflate"}


def save(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


# --------------------------------------------------------------------------- universe
def sic_to_sector(sic: int | None) -> str:
    if sic is None or pd.isna(sic):
        return "Unknown"
    s = int(sic)
    if 1300 <= s <= 1399 or 2900 <= s <= 2999:
        return "Energy"
    if 2830 <= s <= 2836 or 3841 <= s <= 3851 or 8000 <= s <= 8099 or s == 5122:
        return "Health Care"
    if 3711 <= s <= 3716 or 2200 <= s <= 2399 or 3900 <= s <= 3999 or 7000 <= s <= 7299 \
            or 5200 <= s <= 5399 or 5500 <= s <= 5999 and s != 5912:
        return "Consumer Discretionary"
    if 100 <= s <= 999 or 2000 <= s <= 2199 or 5400 <= s <= 5499 or s == 5912 or 2840 <= s <= 2844:
        return "Consumer Staples"
    if 3570 <= s <= 3579 or 3600 <= s <= 3699 or 3800 <= s <= 3840 or 7370 <= s <= 7379:
        return "Information Technology"
    if 4800 <= s <= 4899 or 2700 <= s <= 2799 or 7800 <= s <= 7999:
        return "Communication Services"
    if 4900 <= s <= 4999:
        return "Utilities"
    if 6500 <= s <= 6599 or s == 6798:
        return "Real Estate"
    if 6000 <= s <= 6799:
        return "Financials"
    if 1000 <= s <= 1499 or 2400 <= s <= 2699 or 2800 <= s <= 2899 or 3000 <= s <= 3399:
        return "Materials"
    return "Industrials"


def normalize_symbol(symbol: str) -> str:
    """One spelling per share class: 'BRK-B' and 'BRK.B' both become 'BRK.B' (Alpaca's format)."""
    cleaned = str(symbol).split("(")[0].strip().upper()  # e.g. "RVTY (PREVIOUSLY PKI)" -> "RVTY"
    return cleaned.replace("-", ".").replace("/", ".")


def membership_intervals(history: pd.DataFrame, start: pd.Timestamp) -> pd.DataFrame:
    """history: one row per change date with the full member list. Returns one row per
    continuous membership spell: symbol, effective_from, effective_to (inclusive)."""
    columns = list(history.columns)
    date_col = next((c for c in columns if "date" in str(c).lower()), columns[0])
    tickers_col = next((c for c in columns if "ticker" in str(c).lower() or "symbol" in str(c).lower()),
                       next(c for c in columns if c != date_col))
    history = history.assign(**{date_col: pd.to_datetime(history[date_col], utc=True)})
    history = history.sort_values(date_col).reset_index(drop=True)
    dates = list(history[date_col])
    members = [set(normalize_symbol(t) for t in str(x).split(",") if t.strip()) for x in history[tickers_col]]
    spells, open_since = [], {}
    for i, current in enumerate(members):
        for symbol in current - set(open_since):
            open_since[symbol] = dates[i]
        for symbol in set(open_since) - current:
            spells.append((symbol, open_since.pop(symbol), dates[i] - pd.Timedelta(days=1)))
    spells += [(symbol, since, FAR_FUTURE) for symbol, since in open_since.items()]
    frame = pd.DataFrame(spells, columns=["symbol", "effective_from", "effective_to"])
    return frame[frame.effective_to >= start].sort_values(["symbol", "effective_from"]).reset_index(drop=True)


def step_universe(args: argparse.Namespace) -> None:
    start = pd.Timestamp(args.start, tz="UTC")
    log("Downloading historical S&P 500 membership...")
    history = pd.read_csv(io.StringIO(http_get(HIST_URL).text))
    spells = membership_intervals(history, start)
    current = pd.read_csv(io.StringIO(http_get(CURRENT_URL).text))
    lower = {c.lower(): c for c in current.columns}
    sym_col = next(lower[c] for c in ("symbol", "ticker") if c in lower)
    sector_col = next((c for c in current.columns if "sector" in c.lower()), None)
    cik_col = lower.get("cik")
    current["symbol"] = current[sym_col].map(normalize_symbol)
    gics = dict(zip(current.symbol, current[sector_col])) if sector_col else {}
    cik_map = {s: str(int(c)).zfill(10) for s, c in zip(current.symbol, current[cik_col]) if pd.notna(c)} if cik_col else {}

    log("Looking up SEC CIK numbers...")
    headers = sec_headers()
    tickers = http_get(SEC_TICKERS_URL, headers=headers).json()
    sec_map = {str(v["ticker"]).upper().replace("-", "."): str(v["cik_str"]).zfill(10) for v in tickers.values()}
    symbols = sorted(spells.symbol.unique())
    ciks = {s: cik_map.get(s) or sec_map.get(s) for s in symbols}

    sectors, sources = {}, {}
    missing = [s for s in symbols if s not in gics and ciks.get(s)]
    log(f"Sectors: {sum(s in gics for s in symbols)} from GICS; looking up {len(missing)} via SEC industry codes...")
    for symbol in symbols:
        if symbol in gics:
            sectors[symbol], sources[symbol] = gics[symbol], "gics"
    for n, symbol in enumerate(missing, 1):
        response = http_get(SEC_SUBMISSIONS_URL.format(cik=ciks[symbol]), headers=headers, pause=0.12)
        sic = response.json().get("sic") if response.ok else None
        sectors[symbol] = sic_to_sector(int(sic) if sic not in (None, "") else None)
        sources[symbol] = "sec_sic"
        if n % 25 == 0:
            log(f"  {n}/{len(missing)}")
    spells["sector"] = spells.symbol.map(sectors).fillna("Unknown")
    spells["sector_source"] = spells.symbol.map(sources).fillna("none")
    spells["cik"] = spells.symbol.map(ciks)
    path = OUT / "universe.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    spells.to_csv(path, index=False)
    active = spells[spells.effective_to >= FAR_FUTURE - pd.Timedelta(days=1)].symbol.nunique()
    log(f"Saved {path}: {spells.symbol.nunique()} symbols ever in the index since {args.start} "
        f"({active} current, {spells.symbol.nunique() - active} removed); "
        f"{(spells.sector == 'Unknown').sum()} spells with unknown sector; "
        f"{spells.cik.isna().sum()} spells without a CIK (no fundamentals).")


# --------------------------------------------------------------------------- bars
def fetch_bars(symbols: list[str], start: str, end: str, feed: str, adjustment: str, headers: dict) -> pd.DataFrame:
    params = {"symbols": ",".join(symbols), "timeframe": "1Day", "start": start, "end": end,
              "limit": 10000, "feed": feed, "adjustment": adjustment, "sort": "asc"}
    rows, token = [], None
    while True:
        if token:
            params["page_token"] = token
        response = http_get(ALPACA_URL, headers=headers, params=params)
        if response.status_code in (401, 403):
            raise SystemExit(f"Alpaca refused the request ({response.status_code}): {response.text[:200]}\n"
                             "Check your Alpaca keys; if the message mentions the feed, rerun with --feed iex.")
        response.raise_for_status()
        payload = response.json()
        for symbol, bars in (payload.get("bars") or {}).items():
            rows += [{"timestamp": b["t"], "symbol": symbol, "open": b["o"], "high": b["h"], "low": b["l"],
                      "close": b["c"], "volume": b["v"]} for b in bars]
        token = payload.get("next_page_token")
        if not token:
            return pd.DataFrame(rows)


def step_bars(args: argparse.Namespace) -> None:
    universe = pd.read_csv(OUT / "universe.csv")
    symbols = sorted(set(universe.symbol.astype(str)) | {"SPY"})
    key = settings_value("APCA_API_KEY_ID", "ALPACA_API_KEY")
    secret = settings_value("APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY")
    if not key or not secret:
        raise SystemExit("Alpaca keys not found. Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env.")
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    # Extra history before the universe start so 126-day features and beta are ready on day one.
    bar_start = (pd.Timestamp(args.start) - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
    cache = OUT / "bars_cache"
    chunks = [symbols[i:i + 50] for i in range(0, len(symbols), 50)]
    paths, rejected = [], []
    for n, chunk in enumerate(chunks):
        digest = hashlib.sha1(",".join(chunk + [bar_start, args.end, args.feed]).encode()).hexdigest()[:10]
        path = cache / f"chunk_{n:03d}_{digest}.parquet"
        paths.append(path)
        if path.exists():
            continue
        log(f"Bars chunk {n + 1}/{len(chunks)} ({chunk[0]}..{chunk[-1]})")
        try:
            adjusted = fetch_bars(chunk, bar_start, args.end, args.feed, "all", headers)
            raw = fetch_bars(chunk, bar_start, args.end, args.feed, "raw", headers)
        except requests.HTTPError as error:
            if error.response is None or error.response.status_code != 400:
                raise
            # One bad symbol makes Alpaca reject the whole request; retry one by one.
            log("  Alpaca rejected this batch; retrying symbols individually...")
            adjusted_parts, raw_parts = [], []
            for symbol in chunk:
                try:
                    adjusted_parts.append(fetch_bars([symbol], bar_start, args.end, args.feed, "all", headers))
                    raw_parts.append(fetch_bars([symbol], bar_start, args.end, args.feed, "raw", headers))
                except requests.HTTPError as inner:
                    if inner.response is None or inner.response.status_code != 400:
                        raise
                    rejected.append(symbol)
            adjusted = pd.concat(adjusted_parts, ignore_index=True) if adjusted_parts else pd.DataFrame()
            raw = pd.concat(raw_parts, ignore_index=True) if raw_parts else pd.DataFrame()
        if adjusted.empty:
            frame = pd.DataFrame(columns=["timestamp", "symbol", "open", "high", "low", "close", "volume", "close_raw"])
        elif raw.empty:
            frame = adjusted.assign(close_raw=np.nan)
        else:
            raw = raw[["timestamp", "symbol", "close"]].rename(columns={"close": "close_raw"})
            frame = adjusted.merge(raw, on=["timestamp", "symbol"], how="left")
        save(frame, path)
    frame = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    if rejected:
        log(f"Alpaca rejected {len(rejected)} symbols as invalid: {', '.join(rejected)}")
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    frame = frame.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"])
    save(frame, OUT / "bars.parquet")
    missing = sorted(set(symbols) - set(frame.symbol))
    log(f"Saved {OUT / 'bars.parquet'}: {len(frame):,} rows, {frame.symbol.nunique()} symbols, "
        f"{frame.timestamp.min():%Y-%m-%d} to {frame.timestamp.max():%Y-%m-%d}")
    if missing:
        log(f"{len(missing)} symbols returned no bars (mostly removed or renamed companies): "
            + ", ".join(missing[:40]) + (" ..." if len(missing) > 40 else ""))


# --------------------------------------------------------------------------- fundamentals
def _facts(company: dict, taxonomy: str, tags: list[str], unit: str) -> pd.DataFrame:
    rows = []
    for priority, tag in enumerate(tags):
        concept = company.get("facts", {}).get(taxonomy, {}).get(tag)
        if not concept:
            continue
        for fact in concept.get("units", {}).get(unit, []):
            if "filed" in fact and "end" in fact and fact.get("val") is not None:
                rows.append({"start": fact.get("start"), "end": fact["end"], "val": float(fact["val"]),
                             "filed": fact["filed"], "priority": priority})
    if not rows:
        return pd.DataFrame(columns=["start", "end", "val", "filed", "priority"])
    frame = pd.DataFrame(rows)
    for column in ("start", "end", "filed"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    frame = frame.dropna(subset=["end", "filed"])
    # Point in time: first time each period was reported, preferring the main tag.
    keys = ["start", "end"] if frame.start.notna().any() else ["end"]
    return frame.sort_values(["priority", "filed"]).drop_duplicates(keys, keep="first")


def quarterly_flows(facts: pd.DataFrame) -> pd.DataFrame:
    """Three-month values from direct quarterly facts or differences of year-to-date facts."""
    if facts.empty:
        return pd.DataFrame(columns=["end", "val", "available"])
    f = facts.dropna(subset=["start"]).copy()
    f["days"] = (f.end - f.start).dt.days
    direct = f[f.days.between(80, 100)][["end", "val", "filed"]].rename(columns={"filed": "available"})
    derived = []
    for _, chain in f[f.days.between(80, 380)].groupby("start"):
        chain = chain.sort_values("end")
        for (_, a), (_, b) in zip(chain.iterrows(), chain.iloc[1:].iterrows()):
            if 80 <= (b.end - a.end).days <= 100:
                derived.append({"end": b.end, "val": b.val - a.val, "available": max(a.filed, b.filed)})
    quarters = pd.concat([direct, pd.DataFrame(derived)], ignore_index=True) if derived else direct
    return quarters.sort_values("available").drop_duplicates("end", keep="first").sort_values("end")


def ttm_series(facts: pd.DataFrame) -> pd.DataFrame:
    """Trailing-twelve-month values keyed by period end, with the date they became known."""
    out = []
    q = quarterly_flows(facts).reset_index(drop=True)
    for i in range(3, len(q)):
        window = q.iloc[i - 3:i + 1]
        if 250 <= (window.end.iloc[-1] - window.end.iloc[0]).days <= 300:
            out.append({"end": window.end.iloc[-1], "val": window.val.sum(), "available": window.available.max()})
    if not facts.empty and facts.start.notna().any():
        annual = facts.dropna(subset=["start"])
        annual = annual[(annual.end - annual.start).dt.days.between(350, 380)]
        out += [{"end": r.end, "val": r.val, "available": r.filed} for r in annual.itertuples()]
    if not out:
        return pd.DataFrame(columns=["end", "val", "available"])
    frame = pd.DataFrame(out)
    return frame.sort_values("available").drop_duplicates("end", keep="first").sort_values("end")


def as_of_timeline(series: pd.DataFrame, name: str, lag_name: str | None = None) -> pd.DataFrame:
    """For each date a value became known, the value for the most recent period known so far.
    Optionally also the value for the period about one year earlier (for growth rates)."""
    if series.empty:
        return pd.DataFrame(columns=["available", name] + ([lag_name] if lag_name else []))
    s = series.sort_values("end").reset_index(drop=True)
    if lag_name:
        prior = s[["end", "val"]].rename(columns={"end": "prior_end", "val": "prior_val"})
        s["target"] = s.end - pd.Timedelta(days=365)
        s = pd.merge_asof(s.sort_values("target"), prior.sort_values("prior_end"), left_on="target",
                          right_on="prior_end", direction="nearest", tolerance=pd.Timedelta(days=20))
    rows, best_end = [], None
    for r in s.sort_values(["available", "end"]).itertuples():
        if best_end is None or r.end >= best_end:
            best_end = r.end
            row = {"available": r.available, name: r.val}
            if lag_name:
                row[lag_name] = r.prior_val
            rows.append(row)
    return pd.DataFrame(rows).drop_duplicates("available", keep="last")


def company_fundamentals(company: dict) -> pd.DataFrame:
    parts = []
    for name, tags in FLOW_TAGS.items():
        lag = f"{name}_ttm_prior_year" if name == "revenue" else None
        parts.append(as_of_timeline(ttm_series(_facts(company, "us-gaap", tags, "USD")), f"{name}_ttm", lag))
    for name, tags in INSTANT_TAGS.items():
        facts = _facts(company, "us-gaap", tags, "USD")
        series = facts.rename(columns={"filed": "available"})[["end", "val", "available"]]
        lag = f"{name}_prior_year" if name == "total_assets" else None
        parts.append(as_of_timeline(series, name, lag))
    share_parts = [p for p in (_facts(company, taxonomy, [tag], "shares") for taxonomy, tag in SHARE_TAGS)
                   if not p.empty]
    shares = pd.concat(share_parts, ignore_index=True) if share_parts else pd.DataFrame()
    if not shares.empty:
        shares = shares.sort_values("filed").drop_duplicates("end", keep="first")
        parts.append(as_of_timeline(shares.rename(columns={"filed": "available"})[["end", "val", "available"]],
                                    "shares_outstanding"))
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame()
    timeline = pd.DataFrame({"available": sorted(set().union(*[set(p.available) for p in parts]))})
    for part in parts:
        timeline = pd.merge_asof(timeline, part.sort_values("available"), on="available", direction="backward")
    t = timeline
    equity = t.get("total_equity").where(t.get("total_equity") > 0) if "total_equity" in t else np.nan
    assets = t.get("total_assets").where(t.get("total_assets") > 0) if "total_assets" in t else np.nan
    if "net_income_ttm" in t:
        t["roe"] = t.net_income_ttm / equity
        t["roa"] = t.net_income_ttm / assets
    if {"net_income_ttm", "operating_cash_flow_ttm"}.issubset(t.columns):
        t["accruals"] = (t.net_income_ttm - t.operating_cash_flow_ttm) / assets
    if {"gross_profit_ttm", "revenue_ttm"}.issubset(t.columns):
        t["gross_margin"] = t.gross_profit_ttm / t.revenue_ttm.where(t.revenue_ttm > 0)
    if "revenue_ttm_prior_year" in t:
        t["revenue_growth"] = t.revenue_ttm / t.revenue_ttm_prior_year.where(t.revenue_ttm_prior_year > 0) - 1
    if "total_assets_prior_year" in t:
        t["asset_growth"] = t.total_assets / t.total_assets_prior_year.where(t.total_assets_prior_year > 0) - 1
    # Filings can land after the close; treat each value as usable from the next day.
    t["available_at"] = pd.to_datetime(t.available, utc=True) + pd.Timedelta(days=1)
    return t.drop(columns=["available"])


def step_fundamentals(args: argparse.Namespace) -> None:
    universe = pd.read_csv(OUT / "universe.csv", dtype={"cik": str})
    pairs = universe.dropna(subset=["cik"])[["symbol", "cik"]].drop_duplicates()
    headers = sec_headers()
    cache = OUT / "fundamentals_cache"
    cache.mkdir(parents=True, exist_ok=True)
    ciks = sorted(pairs.cik.str.zfill(10).unique())
    for n, cik in enumerate(ciks, 1):
        path = cache / f"{cik}.parquet"
        if path.exists() and (args.refresh_days is None
                              or time.time() - path.stat().st_mtime < args.refresh_days * 86400):
            continue
        response = http_get(SEC_FACTS_URL.format(cik=cik), headers=headers, pause=0.12)
        frame = company_fundamentals(response.json()) if response.ok else pd.DataFrame()
        save(frame if not frame.empty else pd.DataFrame({"available_at": pd.Series(dtype="datetime64[ns, UTC]")}), path)
        if n % 25 == 0 or n == len(ciks):
            log(f"  SEC companies processed: {n}/{len(ciks)}")
    pieces = []
    for symbol, cik in pairs.itertuples(index=False):
        frame = pd.read_parquet(cache / f"{str(cik).zfill(10)}.parquet")
        if not frame.empty:
            pieces.append(frame.assign(symbol=symbol))
    if not pieces:
        raise SystemExit("No fundamentals were parsed; check SEC_USER_AGENT and your connection.")
    result = pd.concat(pieces, ignore_index=True)
    save(result, OUT / "fundamentals.parquet")
    log(f"Saved {OUT / 'fundamentals.parquet'}: {len(result):,} rows for {result.symbol.nunique()} symbols, "
        f"{result.available_at.min():%Y-%m-%d} to {result.available_at.max():%Y-%m-%d}")


# --------------------------------------------------------------------------- panel
PRICE_FEATURES = ["return_lag_1", "momentum_5", "momentum_21", "momentum_63", "momentum_126", "volatility",
                  "volatility_63", "vol_scaled_momentum", "log_dollar_volume", "volume_change_20", "amihud_20",
                  "range_20", "residual_momentum_21"]
FUNDAMENTAL_FEATURES = ["roe", "roa", "accruals", "gross_margin", "revenue_growth", "asset_growth",
                        "earnings_yield", "book_to_price", "sales_to_price", "log_market_cap"]


def price_features(section: pd.DataFrame) -> pd.DataFrame:
    s = section.sort_values("timestamp").copy()
    c, v = s.close.astype(float), s.volume.astype(float)
    r = c.pct_change(fill_method=None)
    s["raw_return"] = r
    s["return_lag_1"] = r.shift(1)
    for horizon in (5, 21, 63, 126):
        s[f"momentum_{horizon}"] = c.pct_change(horizon, fill_method=None).shift(1)
    s["volatility"] = r.rolling(20, min_periods=10).std().shift(1)
    s["volatility_63"] = r.rolling(63, min_periods=30).std().shift(1)
    s["vol_scaled_momentum"] = s.momentum_21 / s.volatility.replace(0, np.nan)
    dollar = c * v
    s["log_dollar_volume"] = np.log1p(dollar).rolling(20, min_periods=10).mean().shift(1)
    s["volume_change_20"] = (v / v.rolling(20, min_periods=10).mean() - 1).shift(1)
    s["amihud_20"] = (r.abs() / dollar.replace(0, np.nan)).rolling(20, min_periods=10).mean().shift(1)
    s["range_20"] = ((s.high - s.low) / c).rolling(20, min_periods=10).mean().shift(1)
    s["close_raw_lag_1"] = s.close_raw.shift(1) if "close_raw" in s else np.nan
    return s


def step_panel(args: argparse.Namespace) -> None:
    universe = pd.read_csv(OUT / "universe.csv")
    for column in ("effective_from", "effective_to"):
        universe[column] = pd.to_datetime(universe[column], utc=True)
    bars = pd.read_parquet(OUT / "bars.parquet")
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True).astype("datetime64[ns, UTC]")
    market = bars[bars.symbol == "SPY"][["timestamp", "close"]].sort_values("timestamp")
    market["market_return"] = market.close.pct_change(fill_method=None)
    stocks = bars[bars.symbol.isin(universe.symbol)]
    log("Computing price features on full histories...")
    panel = pd.concat([price_features(g) for _, g in stocks.groupby("symbol")], ignore_index=True)
    panel = panel.merge(market[["timestamp", "market_return"]], on="timestamp", how="left")
    betas = []
    for _, g in panel.groupby("symbol"):
        cov = g.raw_return.rolling(126, min_periods=63).cov(g.market_return)
        betas.append((cov / g.market_return.rolling(126, min_periods=63).var()).shift(1))
    panel["beta"] = pd.concat(betas).sort_index()

    # Keep only days when the stock was actually in the index (removes survivorship bias).
    panel = panel.merge(universe[["symbol", "effective_from", "effective_to", "sector"]], on="symbol")
    panel = panel[(panel.timestamp >= panel.effective_from) & (panel.timestamp <= panel.effective_to)]
    panel = panel[panel.timestamp >= pd.Timestamp(args.start, tz="UTC")].copy()

    sector_return = panel.groupby(["timestamp", "sector"]).raw_return.transform("mean")
    panel["residual_return"] = panel.raw_return - panel.beta.fillna(1.0) * panel.market_return - sector_return
    panel = panel.sort_values(["symbol", "timestamp"])
    panel["residual_momentum_21"] = panel.groupby("symbol").residual_return.transform(
        lambda x: np.expm1(np.log1p(x).rolling(21, min_periods=15).sum()).shift(1))

    fundamentals_path = OUT / "fundamentals.parquet"
    if fundamentals_path.exists():
        log("Joining point-in-time fundamentals...")
        fundamentals = pd.read_parquet(fundamentals_path)
        fundamentals["available_at"] = pd.to_datetime(fundamentals.available_at, utc=True).astype("datetime64[ns, UTC]")
        keep = ["symbol", "available_at"] + [c for c in ["roe", "roa", "accruals", "gross_margin", "revenue_growth",
                                                         "asset_growth", "net_income_ttm", "total_equity",
                                                         "revenue_ttm", "shares_outstanding"] if c in fundamentals]
        fundamentals = fundamentals[keep].sort_values("available_at")
        panel = pd.merge_asof(panel.sort_values("timestamp"), fundamentals, left_on="timestamp",
                              right_on="available_at", by="symbol", direction="backward")
        if "shares_outstanding" in panel:
            cap = (panel.shares_outstanding * panel.close_raw_lag_1).where(lambda x: x > 0)
            panel["log_market_cap"] = np.log(cap)
            panel["earnings_yield"] = panel.get("net_income_ttm") / cap
            panel["book_to_price"] = panel.get("total_equity") / cap
            panel["sales_to_price"] = panel.get("revenue_ttm") / cap
    else:
        log("No fundamentals.parquet found; building a price-only panel.")

    features = [f for f in PRICE_FEATURES + FUNDAMENTAL_FEATURES if f in panel.columns]
    panel = panel.replace([np.inf, -np.inf], np.nan)
    # One version per feature: cross-sectional rank centered on zero (robust to outliers and
    # comparable across years). Raw beta and sector stay because V008 residualizes with them.
    ranked = panel.groupby("timestamp")[features].rank(pct=True) - 0.5
    ranked.columns = [f"rank_{c}" for c in features]
    result = pd.concat([panel[["timestamp", "symbol", "close", "sector", "beta"]], ranked], axis=1)
    counts = result.groupby("timestamp").symbol.transform("nunique")
    result = result[counts >= args.min_symbols].sort_values(["timestamp", "symbol"]).reset_index(drop=True)
    path = OUT / "model_panel.parquet"
    save(result, path)
    coverage = result[[f"rank_{c}" for c in features]].notna().mean().round(3)
    log(f"Saved {path}: {len(result):,} rows, {result.symbol.nunique()} symbols, {result.timestamp.nunique()} dates, "
        f"median {result.groupby('timestamp').symbol.nunique().median():.0f} names per date")
    log("Feature coverage:\n" + coverage.to_string())


# --------------------------------------------------------------------------- main
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("step", choices=["universe", "bars", "fundamentals", "panel", "all"])
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    p.add_argument("--feed", default="sip", help="sip = full market (default), iex = single exchange")
    p.add_argument("--min-symbols", type=int, default=100)
    p.add_argument("--refresh-days", type=float, default=None,
                   help="re-download SEC fundamentals cached more than this many days ago (forward testing)")
    args = p.parse_args()
    steps = ["universe", "bars", "fundamentals", "panel"] if args.step == "all" else [args.step]
    for step in steps:
        log(f"\n=== {step} ===")
        {"universe": step_universe, "bars": step_bars, "fundamentals": step_fundamentals,
         "panel": step_panel}[step](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
