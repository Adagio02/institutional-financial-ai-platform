from datetime import UTC, datetime
from decimal import Decimal

import pytest

from finai.domain.market_data.entities import MarketBar
from finai.domain.market_data.enums import BarInterval
from finai.domain.market_data.validation import (
    normalize_symbol,
    validate_market_bar,
)


def test_normalize_symbol() -> None:
    assert normalize_symbol(" aapl ") == "AAPL"


def test_reject_empty_symbol() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        normalize_symbol("   ")


def test_valid_market_bar() -> None:
    bar = MarketBar(
        symbol="AAPL",
        interval=BarInterval.ONE_DAY,
        timestamp=datetime.now(UTC),
        open_price=Decimal("100"),
        high_price=Decimal("110"),
        low_price=Decimal("95"),
        close_price=Decimal("105"),
        volume=Decimal("100000"),
        provider="mock",
    )

    validate_market_bar(bar)


def test_reject_invalid_high_price() -> None:
    bar = MarketBar(
        symbol="AAPL",
        interval=BarInterval.ONE_DAY,
        timestamp=datetime.now(UTC),
        open_price=Decimal("100"),
        high_price=Decimal("90"),
        low_price=Decimal("80"),
        close_price=Decimal("95"),
        volume=Decimal("100000"),
        provider="mock",
    )

    with pytest.raises(ValueError):
        validate_market_bar(bar)
