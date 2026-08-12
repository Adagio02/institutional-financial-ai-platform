from datetime import (
    UTC,
    datetime,
)

import pytest

from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.market_data.execution_quote import (
    get_executable_reference_price,
)
from finai.domain.market_data.quote import (
    MarketQuote,
)


def create_quote() -> MarketQuote:
    return MarketQuote(
        symbol="TEST",
        bid=99.0,
        ask=101.0,
        last=100.0,
        timestamp=datetime.now(UTC),
        provider="test",
    )


def test_buy_uses_ask() -> None:
    result = get_executable_reference_price(
        quote=create_quote(),
        side=OrderSide.BUY,
    )

    assert result == pytest.approx(101.0)


def test_sell_uses_bid() -> None:
    result = get_executable_reference_price(
        quote=create_quote(),
        side=OrderSide.SELL,
    )

    assert result == pytest.approx(99.0)


def test_invalid_crossed_quote_is_rejected() -> None:
    quote = MarketQuote(
        symbol="TEST",
        bid=101.0,
        ask=99.0,
        last=100.0,
        timestamp=datetime.now(UTC),
        provider="test",
    )

    with pytest.raises(
        ValueError,
        match="ask cannot be lower",
    ):
        get_executable_reference_price(
            quote=quote,
            side=OrderSide.BUY,
        )
