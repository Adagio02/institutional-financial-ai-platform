from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)

from finai.domain.market_data.quote import (
    MarketQuote,
)
from finai.infrastructure.market_data.alpaca_market_data_client import (
    AlpacaMarketDataClient,
)


class AlpacaQuoteProvider:
    def __init__(
        self,
        *,
        client: AlpacaMarketDataClient,
    ) -> None:
        self._client = client

    def get_quote(
        self,
        *,
        symbol: str,
    ) -> MarketQuote:
        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        if not normalized_symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        raw_quote = (
            self._client
            .get_latest_quote(
                symbol=normalized_symbol
            )
        )

        bid = self._positive_float(
            raw_quote.get(
                "bp"
            ),
            field_name="bp",
        )

        ask = self._positive_float(
            raw_quote.get(
                "ap"
            ),
            field_name="ap",
        )

        if ask < bid:
            raise ValueError(
                "Alpaca market quote ask "
                "cannot be lower than bid."
            )

        timestamp = (
            self._parse_timestamp(
                raw_quote.get(
                    "t"
                )
            )
        )

        midpoint = (
            bid
            + ask
        ) / 2.0

        return MarketQuote(
            symbol=normalized_symbol,
            bid=bid,
            ask=ask,
            last=midpoint,
            timestamp=timestamp,
            provider=(
                "alpaca-"
                f"{self._client.feed}"
            ),
        )

    @staticmethod
    def _positive_float(
        value,
        *,
        field_name: str,
    ) -> float:
        if value in {
            None,
            "",
        }:
            raise ValueError(
                f"Alpaca quote field "
                f"{field_name} is missing."
            )

        try:
            result = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                f"Alpaca quote field "
                f"{field_name} is invalid."
            ) from error

        if result <= 0:
            raise ValueError(
                f"Alpaca quote field "
                f"{field_name} must "
                "be positive."
            )

        return result

    @staticmethod
    def _parse_timestamp(
        value,
    ) -> datetime:
        if value in {
            None,
            "",
        }:
            raise ValueError(
                "Alpaca quote timestamp "
                "is missing."
            )

        raw = str(
            value
        ).strip()

        if raw.endswith(
            "Z"
        ):
            raw = (
                raw[:-1]
                + "+00:00"
            )

        try:
            timestamp = (
                datetime
                .fromisoformat(
                    raw
                )
            )

        except ValueError as error:
            raise ValueError(
                "Alpaca quote timestamp "
                "is invalid."
            ) from error

        if timestamp.tzinfo is None:
            timestamp = (
                timestamp.replace(
                    tzinfo=UTC
                )
            )

        return (
            timestamp
            .astimezone(UTC)
        )