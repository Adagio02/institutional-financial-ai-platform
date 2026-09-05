from datetime import UTC, datetime

from finai.domain.market_data.enums import BarInterval
from finai.infrastructure.market_data.mock_provider import (
    MockMarketDataProvider,
)


def test_mock_provider_is_deterministic() -> None:
    provider = MockMarketDataProvider()

    start_time = datetime(2026, 1, 1, tzinfo=UTC)
    end_time = datetime(2026, 1, 5, tzinfo=UTC)

    first_result = provider.get_historical_bars(
        symbol="AAPL",
        interval=BarInterval.ONE_DAY,
        start_time=start_time,
        end_time=end_time,
    )

    second_result = provider.get_historical_bars(
        symbol="AAPL",
        interval=BarInterval.ONE_DAY,
        start_time=start_time,
        end_time=end_time,
    )

    assert first_result == second_result
    assert len(first_result) == 5


def test_mock_provider_produces_valid_prices() -> None:
    provider = MockMarketDataProvider()

    bars = provider.get_historical_bars(
        symbol="BTCUSD",
        interval=BarInterval.ONE_HOUR,
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, 4, tzinfo=UTC),
    )

    assert bars

    for bar in bars:
        assert bar.low_price <= bar.open_price <= bar.high_price
        assert bar.low_price <= bar.close_price <= bar.high_price
        assert bar.volume >= 0
