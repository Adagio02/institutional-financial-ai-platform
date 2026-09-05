from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from finai.core.config import Settings


MARKET_DATA_URL = "https://data.alpaca.markets"


def _pick(mapping: dict[str, Any] | None, *names: str, default: Any = None) -> Any:
    mapping = mapping or {}
    for name in names:
        if name in mapping and mapping[name] is not None:
            return mapping[name]
    return default


class AlpacaFreeOptionsCollector:
    def __init__(self, settings: Settings) -> None:
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY are required in .env.")
        self._headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
        }
        self._trading_url = settings.alpaca_base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(self._headers)

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(6):
            response = self._session.get(url, params=params, timeout=60)
            if response.status_code == 429:
                time.sleep(min(2**attempt, 30))
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("Alpaca rate limit persisted after six retries.")

    def contracts(self, symbol: str, minimum_days: int, maximum_days: int) -> dict[str, Any]:
        today = datetime.now(UTC).date()
        params: dict[str, Any] = {
            "underlying_symbols": symbol,
            "status": "active",
            "expiration_date_gte": (today + timedelta(days=minimum_days)).isoformat(),
            "expiration_date_lte": (today + timedelta(days=maximum_days)).isoformat(),
            "limit": 1000,
        }
        result: dict[str, Any] = {}
        while True:
            payload = self._get(f"{self._trading_url}/v2/options/contracts", params)
            for contract in payload.get("option_contracts", []):
                result[str(contract["symbol"])] = contract
            token = payload.get("next_page_token")
            if not token:
                return result
            params["page_token"] = token

    def underlying_midpoint(self, symbol: str) -> float:
        payload = self._get(
            f"{MARKET_DATA_URL}/v2/stocks/{symbol}/snapshot",
            {"feed": "iex"},
        )
        quote = _pick(payload, "latestQuote", "latest_quote", default={})
        bid = float(_pick(quote, "bp", "bid_price", default=0.0))
        ask = float(_pick(quote, "ap", "ask_price", default=0.0))
        if bid > 0 and ask >= bid:
            return (bid + ask) / 2.0

        # IEX bid/ask can be empty outside regular hours. Snapshot trade/bar
        # values are real observed prices and provide a safe after-hours fallback.
        candidates = (
            ("latest trade", _pick(payload, "latestTrade", "latest_trade", default={})),
            ("minute bar", _pick(payload, "minuteBar", "minute_bar", default={})),
            ("daily bar", _pick(payload, "dailyBar", "daily_bar", default={})),
            (
                "previous daily bar",
                _pick(payload, "prevDailyBar", "prev_daily_bar", default={}),
            ),
        )
        for source, observation in candidates:
            value = float(_pick(observation, "p", "price", "c", "close", default=0.0))
            if value > 0:
                print(f"  {symbol}: using {source} price {value:.4f}")
                return value
        raise RuntimeError(
            f"No valid underlying IEX quote, trade, or bar price for {symbol}."
        )

    def snapshots(self, symbol: str) -> dict[str, Any]:
        params: dict[str, Any] = {"feed": "indicative", "limit": 1000}
        result: dict[str, Any] = {}
        while True:
            payload = self._get(
                f"{MARKET_DATA_URL}/v1beta1/options/snapshots/{symbol}", params
            )
            result.update(payload.get("snapshots", {}))
            token = payload.get("next_page_token")
            if not token:
                return result
            params["page_token"] = token


def _contract_type(contract: dict[str, Any]) -> str:
    value = str(_pick(contract, "type", "option_type", default="")).upper()
    return {"CALL": "C", "PUT": "P", "C": "C", "P": "P"}.get(value, "")


def collect_once(
    collector: AlpacaFreeOptionsCollector,
    symbols: list[str],
    minimum_days: int,
    maximum_days: int,
    maximum_moneyness: float,
) -> list[dict[str, Any]]:
    collected_at = pd.Timestamp.now(tz="UTC").floor("min")
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        print(f"Collecting {symbol} at {collected_at}...")
        spot = collector.underlying_midpoint(symbol)
        contracts = collector.contracts(symbol, minimum_days, maximum_days)
        snapshots = collector.snapshots(symbol)
        for contract_symbol, snapshot in snapshots.items():
            contract = contracts.get(contract_symbol)
            if not contract:
                continue
            strike = float(_pick(contract, "strike_price", "strike", default=0.0))
            if strike <= 0 or abs(strike / spot - 1.0) > maximum_moneyness:
                continue
            quote = _pick(snapshot, "latestQuote", "latest_quote", default={})
            greeks = _pick(snapshot, "greeks", default={})
            daily = _pick(snapshot, "dailyBar", "daily_bar", default={})
            bid = float(_pick(quote, "bp", "bid_price", default=0.0))
            ask = float(_pick(quote, "ap", "ask_price", default=0.0))
            iv = float(
                _pick(snapshot, "impliedVolatility", "implied_volatility", default=0.0)
            )
            delta = float(_pick(greeks, "delta", default=float("nan")))
            gamma = float(_pick(greeks, "gamma", default=float("nan")))
            open_interest = float(_pick(contract, "open_interest", default=0.0))
            volume = float(_pick(daily, "v", "volume", default=0.0))
            option_type = _contract_type(contract)
            if not (
                bid >= 0
                and ask >= bid
                and iv > 0
                and pd.notna(delta)
                and pd.notna(gamma)
                and option_type
            ):
                continue
            rows.append(
                {
                    "timestamp": collected_at,
                    "underlying_symbol": symbol,
                    "expiration": _pick(contract, "expiration_date", "expiration"),
                    "strike": strike,
                    "option_type": option_type,
                    "bid_price": bid,
                    "ask_price": ask,
                    "implied_volatility": iv,
                    "delta": delta,
                    "gamma": gamma,
                    "open_interest": max(open_interest, 0.0),
                    "volume": max(volume, 0.0),
                    "underlying_price": spot,
                    "contract_symbol": contract_symbol,
                    "feed": "indicative",
                    "open_interest_date": _pick(contract, "open_interest_date"),
                }
            )
        print(f"  accepted {sum(row['underlying_symbol'] == symbol for row in rows)} rows")
    return rows


def save(rows: list[dict[str, Any]], output: Path) -> None:
    if not rows:
        raise RuntimeError("No valid option snapshots were collected.")
    new = pd.DataFrame(rows)
    if output.exists():
        existing = pd.read_csv(output)
        combined = pd.concat([existing, new], ignore_index=True)
    else:
        combined = new
    keys = ["timestamp", "underlying_symbol", "expiration", "strike", "option_type"]
    combined = combined.drop_duplicates(keys, keep="last").sort_values(keys)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".partial.csv")
    combined.to_csv(temporary, index=False)
    temporary.replace(output)
    print(
        f"Saved {len(combined):,} rows, "
        f"{combined['timestamp'].nunique()} samples, "
        f"{combined['underlying_symbol'].nunique()} symbols to {output}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="AAPL,MSFT,AMZN,NVDA,SPY,QQQ")
    parser.add_argument("--samples", type=int, default=6)
    parser.add_argument("--interval-seconds", type=int, default=900)
    parser.add_argument("--minimum-days", type=int, default=14)
    parser.add_argument("--maximum-days", type=int, default=120)
    parser.add_argument("--maximum-moneyness", type=float, default=0.20)
    parser.add_argument("--output", default="data/research/options_chain.csv")
    args = parser.parse_args()
    if args.samples < 1 or args.interval_seconds < 0:
        raise ValueError("samples must be positive and interval-seconds cannot be negative.")
    symbols = sorted({value.strip().upper() for value in args.symbols.split(",") if value.strip()})
    collector = AlpacaFreeOptionsCollector(Settings())
    output = Path(args.output)
    for sample in range(args.samples):
        print(f"Sample {sample + 1}/{args.samples}")
        rows = collect_once(
            collector,
            symbols,
            args.minimum_days,
            args.maximum_days,
            args.maximum_moneyness,
        )
        save(rows, output)
        if sample + 1 < args.samples:
            time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
