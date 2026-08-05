import pytest

from finai.infrastructure.market_data.factory import (
    create_market_data_provider,
)
from finai.infrastructure.market_data.mock_provider import (
    MockMarketDataProvider,
)
from finai.infrastructure.market_data.yfinance_provider import (
    YFinanceMarketDataProvider,
)
from finai.core.exceptions import UnsupportedProviderError


@pytest.mark.parametrize("name", ["mock", "stub", "MOCK"])
def test_factory_creates_mock_provider(name: str) -> None:
    provider = create_market_data_provider(name)

    assert isinstance(provider, MockMarketDataProvider)


@pytest.mark.parametrize("name", ["yfinance", "yahoo"])
def test_factory_creates_yfinance_provider(name: str) -> None:
    provider = create_market_data_provider(name)

    assert isinstance(provider, YFinanceMarketDataProvider)


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(
        UnsupportedProviderError,
        match="Unsupported",
    ):
        create_market_data_provider("unknown")
