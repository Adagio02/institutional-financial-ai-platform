from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    UTC,
    datetime,
)
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaQuoteGuardResult:
    symbol: str

    bid_price: float

    ask_price: float

    midpoint: float

    spread_bps: float

    reference_price: float

    reference_deviation_bps: float

    quote_timestamp: datetime

    quote_age_seconds: float


class AlpacaQuoteGuard:
    def __init__(
        self,
        *,
        maximum_age_seconds: int,
        maximum_spread_bps: float,
        maximum_reference_deviation_bps: float,
    ) -> None:
        if maximum_age_seconds <= 0:
            raise ValueError(
                "maximum_age_seconds "
                "must be positive."
            )

        if maximum_spread_bps <= 0:
            raise ValueError(
                "maximum_spread_bps "
                "must be positive."
            )

        if (
            maximum_reference_deviation_bps
            <= 0
        ):
            raise ValueError(
                "maximum_reference_deviation_bps "
                "must be positive."
            )

        self._maximum_age_seconds = (
            maximum_age_seconds
        )

        self._maximum_spread_bps = (
            maximum_spread_bps
        )

        self._maximum_reference_deviation_bps = (
            maximum_reference_deviation_bps
        )

    def validate_quote(
        self,
        *,
        symbol: str,
        quote: dict[str, Any],
        reference_price: float,
        now: datetime | None = None,
    ) -> AlpacaQuoteGuardResult:
        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        if not normalized_symbol:
            raise ValueError(
                "symbol cannot be blank."
            )

        if reference_price <= 0:
            raise ValueError(
                "reference_price must "
                "be positive."
            )

        bid_price = self._positive_float(
            quote.get(
                "bp"
            ),
            field_name="bp",
        )

        ask_price = self._positive_float(
            quote.get(
                "ap"
            ),
            field_name="ap",
        )

        if ask_price < bid_price:
            raise ValueError(
                "Alpaca latest quote has "
                "ask below bid."
            )

        quote_timestamp = (
            self._parse_timestamp(
                quote.get(
                    "t"
                )
            )
        )

        resolved_now = (
            now
            or datetime.now(UTC)
        )

        if resolved_now.tzinfo is None:
            resolved_now = (
                resolved_now
                .replace(
                    tzinfo=UTC
                )
            )

        quote_age_seconds = (
            resolved_now
            - quote_timestamp
        ).total_seconds()

        if quote_age_seconds < -5:
            raise ValueError(
                "Alpaca quote timestamp "
                "is unexpectedly in "
                "the future."
            )

        if (
            quote_age_seconds
            > self._maximum_age_seconds
        ):
            raise ValueError(
                "Latest Alpaca quote "
                "is stale. "
                f"symbol={normalized_symbol}, "
                f"age_seconds="
                f"{quote_age_seconds:.3f}."
            )

        midpoint = (
            bid_price
            + ask_price
        ) / 2.0

        if midpoint <= 0:
            raise ValueError(
                "Alpaca quote midpoint "
                "must be positive."
            )

        spread_bps = (
            (
                ask_price
                - bid_price
            )
            / midpoint
            * 10000.0
        )

        if (
            spread_bps
            > self._maximum_spread_bps
        ):
            raise ValueError(
                "Alpaca bid/ask spread "
                "exceeds the configured "
                "V2.8 limit. "
                f"spread_bps="
                f"{spread_bps:.3f}."
            )

        reference_deviation_bps = (
            abs(
                reference_price
                - midpoint
            )
            / midpoint
            * 10000.0
        )

        if (
            reference_deviation_bps
            > (
                self
                ._maximum_reference_deviation_bps
            )
        ):
            raise ValueError(
                "FinAI reference price "
                "deviates too far from "
                "the latest Alpaca quote. "
                f"deviation_bps="
                f"{reference_deviation_bps:.3f}."
            )

        return AlpacaQuoteGuardResult(
            symbol=normalized_symbol,
            bid_price=bid_price,
            ask_price=ask_price,
            midpoint=midpoint,
            spread_bps=spread_bps,
            reference_price=(
                reference_price
            ),
            reference_deviation_bps=(
                reference_deviation_bps
            ),
            quote_timestamp=(
                quote_timestamp
            ),
            quote_age_seconds=(
                quote_age_seconds
            ),
        )

    @staticmethod
    def _positive_float(
        value: Any,
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
        value: Any,
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
            parsed = (
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

        if parsed.tzinfo is None:
            parsed = (
                parsed.replace(
                    tzinfo=UTC
                )
            )

        return (
            parsed
            .astimezone(UTC)
        )