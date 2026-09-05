from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import pandas as pd
import requests

from finai.core.config import Settings


API_URL = "https://data.alpaca.markets/v2/stocks/quotes"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,AMZN,GOOGL,META,NVDA,TSLA,JPM,XOM,UNH",
    )
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--feed", choices=["iex", "sip"], default="iex")
    parser.add_argument(
        "--output",
        default="data/research/historical_quotes.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = arguments()
    settings = Settings()

    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        raise RuntimeError(
            "ALPACA_API_KEY and ALPACA_SECRET_KEY are missing from .env."
        )

    symbols = sorted(
        {
            symbol.strip().upper()
            for symbol in args.symbols.split(",")
            if symbol.strip()
        }
    )

    if len(symbols) < 2:
        raise ValueError("V5.1 requires at least two symbols.")

    headers = {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }

    params = {
        "symbols": ",".join(symbols),
        "start": args.start,
        "end": args.end,
        "feed": args.feed,
        "limit": 10000,
        "sort": "asc",
    }

    # Keep the final quote observed in each minute for each symbol.
    minute_quotes: dict[tuple[pd.Timestamp, str], dict[str, object]] = {}
    page = 0

    while True:
        page += 1

        for attempt in range(6):
            response = requests.get(
                API_URL,
                headers=headers,
                params=params,
                timeout=60,
            )

            if response.status_code == 429:
                delay = min(2 ** attempt, 30)
                print(f"Rate limited; waiting {delay} seconds...")
                time.sleep(delay)
                continue

            response.raise_for_status()
            break
        else:
            raise RuntimeError("Alpaca rate limit persisted after retries.")

        payload = response.json()
        quote_groups = payload.get("quotes", {})

        for symbol, quotes in quote_groups.items():
            for quote in quotes:
                timestamp = pd.to_datetime(
                    quote.get("t"),
                    utc=True,
                    errors="coerce",
                )

                if pd.isna(timestamp):
                    continue

                row = {
                    "timestamp": timestamp.floor("min"),
                    "symbol": symbol.upper(),
                    "bid_price": quote.get("bp"),
                    "ask_price": quote.get("ap"),
                    "bid_size": quote.get("bs"),
                    "ask_size": quote.get("as"),
                    "_original_timestamp": timestamp,
                }

                key = (row["timestamp"], row["symbol"])
                previous = minute_quotes.get(key)

                if (
                    previous is None
                    or timestamp > previous["_original_timestamp"]
                ):
                    minute_quotes[key] = row

        print(
            f"Page {page}: "
            f"{sum(len(items) for items in quote_groups.values()):,} quotes; "
            f"{len(minute_quotes):,} minute snapshots"
        )

        token = payload.get("next_page_token")

        if not token:
            break

        params["page_token"] = token

    rows = list(minute_quotes.values())

    if not rows:
        raise RuntimeError(
            "Alpaca returned no quotes. Check dates, symbols, and feed access."
        )

    frame = pd.DataFrame(rows).drop(columns="_original_timestamp")

    for column in ["bid_price", "ask_price", "bid_size", "ask_size"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    valid = (
        frame["bid_price"].gt(0)
        & frame["ask_price"].ge(frame["bid_price"])
        & frame["bid_size"].gt(0)
        & frame["ask_size"].gt(0)
    )

    frame = (
        frame.loc[valid]
        .sort_values(["timestamp", "symbol"])
        .reset_index(drop=True)
    )

    counts = frame.groupby("timestamp")["symbol"].nunique()
    valid_times = counts[counts >= 2].index
    frame = frame[frame["timestamp"].isin(valid_times)].copy()

    if frame.empty:
        raise RuntimeError(
            "No synchronized cross-sectional quote snapshots were produced."
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".partial.csv")

    frame.to_csv(
        temporary,
        index=False,
        quoting=csv.QUOTE_MINIMAL,
    )
    temporary.replace(output)

    print("")
    print(f"Created: {output.resolve()}")
    print(f"Rows: {len(frame):,}")
    print(f"Symbols: {frame['symbol'].nunique():,}")
    print(f"Minute snapshots: {frame['timestamp'].nunique():,}")
    print(f"Start: {frame['timestamp'].min()}")
    print(f"End: {frame['timestamp'].max()}")


if __name__ == "__main__":
    main()
