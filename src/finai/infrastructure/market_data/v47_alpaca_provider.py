from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from finai.domain.market_data.entities import MarketBar
from finai.domain.market_data.enums import BarInterval
from finai.infrastructure.market_data.alpaca_market_data_client import (
    ALPACA_DATA_BASE_URL,
    AlpacaMarketDataClient,
)


ALPACA_TIMEFRAME_BY_INTERVAL = {
    "1m": "1Min",
    "5m": "5Min",
    "15m": "15Min",
    "30m": "30Min",
    "1h": "1Hour",
    "1d": "1Day",
}


class V47AlpacaHistoricalProvider:
    """
    Domain-level MarketDataProvider adapter over the project's current
    low-level AlpacaMarketDataClient.

    The low-level client returns Alpaca JSON. This adapter:
      - translates BarInterval -> Alpaca timeframe;
      - follows page_token pagination;
      - converts raw Alpaca bars into finai.domain.market_data.MarketBar;
      - keeps credentials inside the existing Settings/client path.
    """

    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        feed: str = "iex",
        timeout_seconds: float = 15.0,
        request_limit: int = 10_000,
    ) -> None:
        if request_limit <= 0:
            raise ValueError(
                "request_limit must be positive."
            )

        self._client = AlpacaMarketDataClient(
            api_key=api_key,
            secret_key=secret_key,
            base_url=ALPACA_DATA_BASE_URL,
            feed=feed,
            timeout_seconds=timeout_seconds,
        )
        self._request_limit = int(
            request_limit
        )

    @property
    def name(self) -> str:
        return "alpaca"

    @staticmethod
    def _timeframe(
        interval: BarInterval,
    ) -> str:
        value = str(interval.value)
        if value not in ALPACA_TIMEFRAME_BY_INTERVAL:
            raise ValueError(
                "Unsupported V4.7 Alpaca interval: "
                f"{value}"
            )
        return ALPACA_TIMEFRAME_BY_INTERVAL[value]

    @staticmethod
    def _parse_timestamp(
        value: str,
    ) -> datetime:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = (
                normalized[:-1]
                + "+00:00"
            )
        parsed = datetime.fromisoformat(
            normalized
        )
        if parsed.tzinfo is None:
            raise ValueError(
                "Alpaca returned a naive timestamp."
            )
        return parsed

    @classmethod
    def _to_market_bar(
        cls,
        *,
        symbol: str,
        interval: BarInterval,
        payload: dict[str, Any],
    ) -> MarketBar:
        required = (
            "t",
            "o",
            "h",
            "l",
            "c",
            "v",
        )
        missing = [
            key
            for key in required
            if key not in payload
        ]
        if missing:
            raise ValueError(
                "Alpaca bar is missing fields: "
                + ", ".join(missing)
            )

        return MarketBar(
            symbol=symbol,
            interval=interval,
            timestamp=cls._parse_timestamp(
                str(payload["t"])
            ),
            open_price=Decimal(
                str(payload["o"])
            ),
            high_price=Decimal(
                str(payload["h"])
            ),
            low_price=Decimal(
                str(payload["l"])
            ),
            close_price=Decimal(
                str(payload["c"])
            ),
            volume=Decimal(
                str(payload["v"])
            ),
            provider="alpaca",
        )

    def get_historical_bars(
        self,
        *,
        symbol: str,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[MarketBar]:
        normalized_symbol = (
            symbol.strip().upper()
        )
        timeframe = self._timeframe(
            interval
        )

        bars: list[MarketBar] = []
        page_token: str | None = None

        while True:
            response = (
                self._client
                .get_historical_bars(
                    symbol=normalized_symbol,
                    timeframe=timeframe,
                    start=start_time.isoformat(),
                    end=end_time.isoformat(),
                    limit=self._request_limit,
                    page_token=page_token,
                )
            )

            raw_bars = response.get(
                "bars",
                [],
            )
            for raw_bar in raw_bars:
                if not isinstance(
                    raw_bar,
                    dict,
                ):
                    raise ValueError(
                        "Unexpected Alpaca bar payload."
                    )
                bars.append(
                    self._to_market_bar(
                        symbol=normalized_symbol,
                        interval=interval,
                        payload=raw_bar,
                    )
                )

            token = response.get(
                "next_page_token"
            )
            if (
                token is None
                or str(token).strip() == ""
            ):
                break

            page_token = str(token)

        return bars
