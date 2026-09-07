from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://data.alpaca.markets/v2/stocks/bars"


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("PASTE_"):
        raise RuntimeError(f"{name} is not loaded with a real value")
    return value


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--universe", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--feed", default="iex")
    a = p.parse_args()
    universe = pd.read_csv(a.universe)
    symbols = sorted(set(universe.symbol.astype(str).str.upper()))
    request_symbols = symbols + (["SPY"] if "SPY" not in symbols else [])
    headers = {
        "APCA-API-KEY-ID": require("APCA_API_KEY_ID"),
        "APCA-API-SECRET-KEY": require("APCA_API_SECRET_KEY"),
    }
    params = {
        "symbols": ",".join(request_symbols), "timeframe": "1Day",
        "start": a.start, "end": a.end, "limit": 10000,
        "feed": a.feed, "adjustment": "all", "sort": "asc",
    }
    rows, token = [], None
    while True:
        if token:
            params["page_token"] = token
        response = requests.get(URL, params=params, headers=headers, timeout=60)
        if response.status_code == 429:
            time.sleep(5)
            continue
        response.raise_for_status()
        payload = response.json()
        for symbol, bars in payload.get("bars", {}).items():
            for bar in bars:
                rows.append({
                    "timestamp": bar["t"], "symbol": symbol,
                    "open": bar["o"], "high": bar["h"], "low": bar["l"],
                    "close": bar["c"], "volume": bar["v"],
                    "trade_count": bar.get("n"), "vwap": bar.get("vw"),
                })
        token = payload.get("next_page_token")
        if not token:
            break
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("Alpaca returned no bars")
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    frame = frame.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"])
    missing = sorted(set(request_symbols).difference(frame.symbol.unique()))
    output = Path(a.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    print(f"Saved {len(frame):,} rows, {frame.symbol.nunique()} symbols to {output}")
    if missing:
        print("Symbols with no returned bars:", ", ".join(missing))


if __name__ == "__main__":
    main()
