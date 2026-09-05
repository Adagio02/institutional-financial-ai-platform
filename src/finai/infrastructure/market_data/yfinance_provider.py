from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
import yfinance as yf

from finai.domain.market_data.entities import MarketBar
from finai.domain.market_data.enums import BarInterval
from finai.domain.market_data.validation import normalize_symbol


class YFinanceMarketDataProvider:
    """Retrieve historical OHLCV market bars from Yahoo Finance."""

    _INTERVAL_MAP: dict[BarInterval, str] = {
        BarInterval.ONE_MINUTE: "1m",
        BarInterval.FIVE_MINUTES: "5m",
        BarInterval.FIFTEEN_MINUTES: "15m",
        BarInterval.ONE_HOUR: "1h",
        BarInterval.ONE_DAY: "1d",
    }

    @property
    def name(self) -> str:
        return "yfinance"

    def get_historical_bars(
        self,
        *,
        symbol: str,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[MarketBar]:
        normalized_symbol = normalize_symbol(symbol)

        if start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware.")

        if end_time.tzinfo is None:
            raise ValueError("end_time must be timezone-aware.")

        if start_time >= end_time:
            raise ValueError("start_time must be earlier than end_time.")

        provider_interval = self._INTERVAL_MAP.get(interval)

        if provider_interval is None:
            raise ValueError(f"Unsupported yfinance interval: {interval.value}")

        dataframe = yf.download(
            tickers=normalized_symbol,
            start=start_time,
            end=end_time,
            interval=provider_interval,
            auto_adjust=False,
            progress=False,
            timeout=15,
            threads=False,
        )

        if dataframe.empty:
            return []

        dataframe = self._normalize_columns(
            dataframe=dataframe,
            symbol=normalized_symbol,
        )

        bars: list[MarketBar] = []

        for timestamp, row in dataframe.iterrows():
            bar_timestamp = self._normalize_timestamp(timestamp)

            open_price = self._to_decimal(row["Open"])
            high_price = self._to_decimal(row["High"])
            low_price = self._to_decimal(row["Low"])
            close_price = self._to_decimal(row["Close"])
            volume = self._to_decimal(row["Volume"])

            # Ignore incomplete rows returned by the provider.
            if any(
                pd.isna(value)
                for value in (
                    row["Open"],
                    row["High"],
                    row["Low"],
                    row["Close"],
                    row["Volume"],
                )
            ):
                continue

            bars.append(
                MarketBar(
                    symbol=normalized_symbol,
                    interval=interval,
                    timestamp=bar_timestamp,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    provider=self.name,
                )
            )

        return bars

    @staticmethod
    def _normalize_columns(
        *,
        dataframe: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:
        """Convert yfinance multi-index columns to normal OHLCV columns."""

        if not isinstance(dataframe.columns, pd.MultiIndex):
            return dataframe

        # Recent yfinance releases may return columns such as:
        # ("Open", "AAPL"), ("High", "AAPL"), etc.
        if symbol in dataframe.columns.get_level_values(-1):
            return dataframe.xs(
                symbol,
                axis=1,
                level=-1,
                drop_level=True,
            )

        dataframe = dataframe.copy()
        dataframe.columns = dataframe.columns.get_level_values(0)

        return dataframe

    @staticmethod
    def _normalize_timestamp(value: Any) -> datetime:
        timestamp = pd.Timestamp(value)

        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(UTC)
        else:
            timestamp = timestamp.tz_convert(UTC)

        return timestamp.to_pydatetime()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        return Decimal(str(value))
