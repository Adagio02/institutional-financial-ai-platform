"""New information from free SEC sources, merged point-in-time into the panel.

SUE (standardized unexpected earnings) - from SEC XBRL company facts:
    EPS for each quarter minus EPS for the same quarter a year earlier, divided by the
    standard deviation of that difference over the last 8 quarters. Usable from the day
    after the filing that reported it. The basis of post-earnings-announcement drift.
Insider purchases - from the SEC Insider Transactions Data Sets (Forms 3/4/5):
    Open-market purchases (code P) and sales (code S) on original Form 4 filings,
    counted over the trailing 90 days by filing date. Published quarterly, so the
    most recent quarter is missing until the SEC posts it.
"""
from __future__ import annotations

import io
import re
import time
import zipfile

import numpy as np
import pandas as pd

import build_expanded_dataset as bx

from . import DATA

EPS_TAGS = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
INSIDER_PAGE = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
INSIDER_PATTERNS = [
    "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{q}_form345.zip",
    "https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets/{q}_form345.zip",
]


def log(message: str) -> None:
    print(message, flush=True)


# ----------------------------------------------------------------------------- SUE
def sue_events(company: dict) -> pd.DataFrame:
    """One row per quarter with a SUE value and the date it became public (+1 day)."""
    facts = bx._facts(company, "us-gaap", EPS_TAGS, "USD/shares")
    quarters = bx.quarterly_flows(facts).reset_index(drop=True)
    if len(quarters) < 8:
        return pd.DataFrame(columns=["available_at", "sue", "period_end"])
    quarters = quarters.sort_values("end").reset_index(drop=True)
    prior = quarters[["end", "val"]].rename(columns={"end": "prior_end", "val": "prior_val"})
    quarters["target"] = quarters.end - pd.Timedelta(days=365)
    merged = pd.merge_asof(quarters.sort_values("target"), prior.sort_values("prior_end"), left_on="target",
                           right_on="prior_end", direction="nearest", tolerance=pd.Timedelta(days=20))
    merged = merged.sort_values("end").reset_index(drop=True)
    merged["change"] = merged.val - merged.prior_val
    scale = merged.change.rolling(8, min_periods=4).std().shift(1)  # history only, excludes current
    merged["sue"] = (merged.change / scale.where(scale > 1e-6)).clip(-10, 10)
    out = merged.dropna(subset=["sue"])
    return pd.DataFrame({"available_at": pd.to_datetime(out.available, utc=True) + pd.Timedelta(days=1),
                         "sue": out.sue.to_numpy(), "period_end": out.end.to_numpy()})


def build_sue(refresh_days: float | None) -> pd.DataFrame:
    universe = pd.read_csv(DATA / "universe.csv", dtype={"cik": str})
    ciks = sorted(universe.cik.dropna().str.zfill(10).unique())
    headers = bx.sec_headers()
    cache = DATA / "eps_cache"
    cache.mkdir(parents=True, exist_ok=True)
    for n, cik in enumerate(ciks, 1):
        path = cache / f"{cik}.parquet"
        fresh = path.exists() and (refresh_days is None or time.time() - path.stat().st_mtime < refresh_days * 86400)
        if fresh:
            continue
        response = bx.http_get(bx.SEC_FACTS_URL.format(cik=cik), headers=headers, pause=0.12)
        frame = sue_events(response.json()) if response.ok else pd.DataFrame()
        if frame.empty:
            frame = pd.DataFrame({"available_at": pd.Series(dtype="datetime64[ns, UTC]"),
                                  "sue": pd.Series(dtype=float), "period_end": pd.Series(dtype="datetime64[ns]")})
        frame.to_parquet(path, index=False)
        if n % 50 == 0 or n == len(ciks):
            log(f"  EPS histories processed: {n}/{len(ciks)}")
    parts = [pd.read_parquet(cache / f"{c}.parquet").assign(cik=c) for c in ciks if (cache / f"{c}.parquet").exists()]
    parts = [p for p in parts if not p.empty]
    result = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["available_at", "sue", "cik"])
    result.to_parquet(DATA / "sue_events.parquet", index=False)
    log(f"SUE events: {len(result):,} quarters for {result.cik.nunique() if len(result) else 0} companies")
    return result


# ----------------------------------------------------------------------------- insiders
def insider_quarter_urls(headers: dict) -> dict[str, list[str]]:
    """Quarter -> candidate URLs, read from the SEC page (paths changed in 2026)."""
    found: dict[str, list[str]] = {}
    try:
        html = bx.http_get(INSIDER_PAGE, headers=headers).text
        for href in re.findall(r'href="([^"]*?(\d{4}q[1-4])_form345\.zip)"', html):
            url = href[0] if href[0].startswith("http") else "https://www.sec.gov" + href[0]
            found.setdefault(href[1], []).append(url)
    except Exception as error:
        log(f"  Could not read the SEC listing page ({error}); trying standard paths.")
    return found


def parse_insider_zip(content: bytes, ciks: set[str]) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = {n.upper().split("/")[-1]: n for n in archive.namelist()}

        def read(table: str, columns: list[str]) -> pd.DataFrame:
            key = next((k for k in names if k.startswith(table)), None)
            if key is None:
                raise ValueError(f"{table} not found in archive")
            with archive.open(names[key]) as stream:
                frame = pd.read_csv(stream, sep="\t", dtype=str, quoting=3, on_bad_lines="skip", low_memory=False)
            frame.columns = [c.strip().upper() for c in frame.columns]
            return frame[[c for c in columns if c in frame.columns]]

        sub = read("SUBMISSION", ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERCIK"])
        trans = read("NONDERIV_TRANS", ["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE"])
    sub = sub[sub.DOCUMENT_TYPE.str.strip() == "4"].copy()  # original Form 4 only, no amendments
    sub["cik"] = sub.ISSUERCIK.str.strip().str.zfill(10)
    sub = sub[sub.cik.isin(ciks)]
    trans = trans[trans.TRANS_CODE.str.strip().isin(["P", "S"])]
    merged = trans.merge(sub, on="ACCESSION_NUMBER")
    merged["value"] = pd.to_numeric(merged.TRANS_SHARES, errors="coerce") * pd.to_numeric(
        merged.TRANS_PRICEPERSHARE, errors="coerce")
    merged["filing_date"] = pd.to_datetime(merged.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    retry = merged.filing_date.isna()
    merged.loc[retry, "filing_date"] = pd.to_datetime(merged.loc[retry, "FILING_DATE"], errors="coerce")
    merged = merged.dropna(subset=["filing_date"])
    code = merged.TRANS_CODE.str.strip()
    merged["buy_value"] = merged.value.where(code == "P", 0.0).fillna(0.0)
    merged["sell_value"] = merged.value.where(code == "S", 0.0).fillna(0.0)
    merged["is_buy"] = (code == "P").astype(float)
    per_filing = merged.groupby(["cik", "filing_date", "ACCESSION_NUMBER"]).agg(
        buy_value=("buy_value", "sum"), sell_value=("sell_value", "sum"), is_buy=("is_buy", "max")).reset_index()
    return per_filing.drop(columns=["ACCESSION_NUMBER"])


def quarters_between(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    periods = pd.period_range(start.tz_localize(None) if start.tzinfo else start,
                              end.tz_localize(None) if end.tzinfo else end, freq="Q")
    return [f"{p.year}q{p.quarter}" for p in periods]


def build_insiders(start: str) -> pd.DataFrame:
    universe = pd.read_csv(DATA / "universe.csv", dtype={"cik": str})
    ciks = set(universe.cik.dropna().str.zfill(10))
    headers = bx.sec_headers()
    listed = insider_quarter_urls(headers)
    cache = DATA / "insider_cache"
    cache.mkdir(parents=True, exist_ok=True)
    wanted = quarters_between(pd.Timestamp(start) - pd.Timedelta(days=120), pd.Timestamp.today())
    unavailable = []
    for quarter in wanted:
        path = cache / f"{quarter}.parquet"
        if path.exists():
            continue
        urls = listed.get(quarter, []) + [p.format(q=quarter) for p in INSIDER_PATTERNS]
        content = None
        for url in dict.fromkeys(urls):
            response = bx.http_get(url, headers=headers, pause=0.2)
            if response.ok and response.content[:2] == b"PK":
                content = response.content
                break
        if content is None:
            unavailable.append(quarter)
            continue
        log(f"  Insider data {quarter}: parsing...")
        parse_insider_zip(content, ciks).to_parquet(path, index=False)
    if unavailable:
        log(f"  Not yet published by the SEC (skipped, will be fetched on a later run): {', '.join(unavailable)}")
    parts = [pd.read_parquet(p) for p in sorted(cache.glob("*.parquet"))]
    result = pd.concat([p for p in parts if not p.empty], ignore_index=True) if parts else pd.DataFrame()
    result.to_parquet(DATA / "insider_filings.parquet", index=False)
    covered = sorted(p.stem for p in cache.glob("*.parquet"))
    log(f"Insider filings: {len(result):,} Form 4 filings with purchases or sales; quarters {covered[0]}..{covered[-1]}"
        if covered else "Insider filings: none downloaded")
    return result


# ----------------------------------------------------------------------------- panel v2
def _asof(panel: pd.DataFrame, events: pd.DataFrame, on: str, columns: list[str], shift_days: int = 0) -> pd.DataFrame:
    left = panel[["symbol", "timestamp"]].copy()
    left["key"] = (left.timestamp - pd.Timedelta(days=shift_days)).astype("datetime64[ns, UTC]")
    right = events[["symbol", on] + columns].rename(columns={on: "key"}).copy()
    right["key"] = pd.to_datetime(right.key, utc=True).astype("datetime64[ns, UTC]")
    merged = pd.merge_asof(left.reset_index().sort_values("key"), right.sort_values("key"), on="key",
                           by="symbol", direction="backward")
    return merged.set_index("index").reindex(panel.index)[columns]


def build_panel_v2() -> pd.DataFrame:
    panel = pd.read_parquet(DATA / "model_panel.parquet")
    panel["timestamp"] = pd.to_datetime(panel.timestamp, utc=True).astype("datetime64[ns, UTC]")
    universe = pd.read_csv(DATA / "universe.csv", dtype={"cik": str})
    symbol_cik = universe.dropna(subset=["cik"])[["symbol", "cik"]].drop_duplicates()
    symbol_cik["cik"] = symbol_cik.cik.str.zfill(10)

    sue_path = DATA / "sue_events.parquet"
    if sue_path.exists():
        sue = pd.read_parquet(sue_path).merge(symbol_cik, on="cik")
        sue["sue_date"] = sue.available_at
        got = _asof(panel, sue, "available_at", ["sue", "sue_date"])
        age = (panel.timestamp - pd.to_datetime(got.sue_date, utc=True)).dt.days
        panel["sue_fresh"] = got.sue.where(age <= 100)
        panel["rank_sue_fresh"] = panel.groupby("timestamp").sue_fresh.rank(pct=True) - 0.5
        log(f"SUE: fresh value (filed within 100 days) for {panel.sue_fresh.notna().mean():.0%} of rows")

    insider_path = DATA / "insider_filings.parquet"
    if insider_path.exists():
        filings = pd.read_parquet(insider_path)
        if not filings.empty:
            filings["available_at"] = pd.to_datetime(filings.filing_date, utc=True) + pd.Timedelta(days=1)
            daily = filings.groupby(["cik", "available_at"])[["buy_value", "sell_value", "is_buy"]].sum().reset_index()
            daily = daily.merge(symbol_cik, on="cik").sort_values(["symbol", "available_at"])
            for column in ("buy_value", "sell_value", "is_buy"):
                daily[f"cum_{column}"] = daily.groupby("symbol")[column].cumsum()
            cums = ["cum_buy_value", "cum_sell_value", "cum_is_buy"]
            now_ = _asof(panel, daily, "available_at", cums).fillna(0.0)
            before = _asof(panel, daily, "available_at", cums, shift_days=90).fillna(0.0)
            window = now_ - before
            total = window.cum_buy_value + window.cum_sell_value
            panel["insider_net_buy_90d"] = ((window.cum_buy_value - window.cum_sell_value) / total.where(total > 0)).fillna(0.0)
            panel["insider_buy_count_90d"] = np.log1p(window.cum_is_buy)
            last_quarter = pd.Period(filings.filing_date.max(), freq="Q")
            covered_until = pd.Timestamp(last_quarter.end_time.date(), tz="UTC")
            for column in ("insider_net_buy_90d", "insider_buy_count_90d"):
                panel.loc[panel.timestamp > covered_until, column] = np.nan  # no data yet: unknown, not zero
                panel[f"rank_{column}"] = panel.groupby("timestamp")[column].rank(pct=True) - 0.5
            log(f"Insider features cover dates through {covered_until:%Y-%m-%d}")

    out = DATA / "model_panel_v2.parquet"
    panel.to_parquet(out, index=False)
    log(f"Saved {out}: {len(panel):,} rows, columns: "
        + ", ".join(c for c in panel.columns if c.startswith("rank_sue") or c.startswith("rank_insider")))
    return panel
