from datetime import (
    UTC,
    datetime,
)
from uuid import uuid4

import pytest

from finai.domain.execution.alpaca_quote_guard import (
    AlpacaQuoteGuard,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)


class FakeTradingClient:
    def __init__(
        self,
    ) -> None:
        self.submit_count = 0

    def submit_order(
        self,
        **kwargs,
    ):
        self.submit_count += 1

        return {
            "id": str(
                uuid4()
            ),
            "client_order_id": (
                kwargs[
                    "client_order_id"
                ]
            ),
            "symbol": (
                kwargs["symbol"]
            ),
            "side": (
                kwargs["side"]
            ),
            "type": (
                kwargs["order_type"]
            ),
            "qty": str(
                kwargs["quantity"]
            ),
            "filled_qty": "0",
            "filled_avg_price": None,
            "time_in_force": (
                kwargs[
                    "time_in_force"
                ]
            ),
            "status": "accepted",
        }


class FakeMarketDataClient:
    def __init__(
        self,
        *,
        bid: float,
        ask: float,
    ) -> None:
        self._bid = bid
        self._ask = ask

    def get_latest_quote(
        self,
        *,
        symbol: str,
    ) -> dict:
        assert symbol == "AAPL"

        return {
            "bp": self._bid,
            "ap": self._ask,
            "bs": 100,
            "as": 100,
            "t": (
                datetime.now(UTC)
                .isoformat()
                .replace(
                    "+00:00",
                    "Z",
                )
            ),
        }


def make_guard(
) -> AlpacaQuoteGuard:
    return AlpacaQuoteGuard(
        maximum_age_seconds=60,
        maximum_spread_bps=100.0,
        maximum_reference_deviation_bps=250.0,
    )


def test_good_quote_allows_submission() -> None:
    trading_client = (
        FakeTradingClient()
    )

    broker = AlpacaPaperBroker(
        client=trading_client,
        market_data_client=(
            FakeMarketDataClient(
                bid=100.0,
                ask=100.1,
            )
        ),
        quote_guard=(
            make_guard()
        ),
    )

    broker.submit(
        order_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=(
            OrderType.MARKET
        ),
        quantity=1.0,
        reference_price=100.05,
        limit_price=None,
        time_in_force="day",
    )

    assert (
        trading_client
        .submit_count
        == 1
    )


def test_bad_reference_blocks_submission() -> None:
    trading_client = (
        FakeTradingClient()
    )

    broker = AlpacaPaperBroker(
        client=trading_client,
        market_data_client=(
            FakeMarketDataClient(
                bid=100.0,
                ask=100.1,
            )
        ),
        quote_guard=(
            make_guard()
        ),
    )

    with pytest.raises(
        ValueError,
        match="reference price",
    ):
        broker.submit(
            order_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=(
                OrderType.MARKET
            ),
            quantity=1.0,
            reference_price=90.0,
            limit_price=None,
            time_in_force="day",
        )

    assert (
        trading_client
        .submit_count
        == 0
    )


def test_wide_spread_blocks_submission() -> None:
    trading_client = (
        FakeTradingClient()
    )

    broker = AlpacaPaperBroker(
        client=trading_client,
        market_data_client=(
            FakeMarketDataClient(
                bid=100.0,
                ask=103.0,
            )
        ),
        quote_guard=(
            make_guard()
        ),
    )

    with pytest.raises(
        ValueError,
        match="spread",
    ):
        broker.submit(
            order_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=(
                OrderType.MARKET
            ),
            quantity=1.0,
            reference_price=101.5,
            limit_price=None,
            time_in_force="day",
        )

    assert (
        trading_client
        .submit_count
        == 0
    )