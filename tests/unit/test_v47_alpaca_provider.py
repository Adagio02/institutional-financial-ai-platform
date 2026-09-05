from __future__ import annotations

from decimal import Decimal

from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.infrastructure.market_data.v47_alpaca_provider import (
    V47AlpacaHistoricalProvider,
)


def test_parse_alpaca_bar() -> None:
    bar = (
        V47AlpacaHistoricalProvider
        ._to_market_bar(
            symbol="AAPL",
            interval=BarInterval("1m"),
            payload={
                "t": "2026-09-01T14:30:00Z",
                "o": 100.0,
                "h": 101.0,
                "l": 99.0,
                "c": 100.5,
                "v": 12345,
            },
        )
    )

    assert bar.symbol == "AAPL"
    assert bar.interval == BarInterval(
        "1m"
    )
    assert bar.close_price == Decimal(
        "100.5"
    )
    assert (
        bar.timestamp.tzinfo
        is not None
    )
