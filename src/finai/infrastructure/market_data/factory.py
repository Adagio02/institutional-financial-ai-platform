from finai.core.exceptions import UnsupportedProviderError
from finai.domain.protocols.market_data_provider import MarketDataProvider
from finai.infrastructure.market_data.mock_provider import (
    MockMarketDataProvider,
)
from finai.infrastructure.market_data.yfinance_provider import (
    YFinanceMarketDataProvider,
)


def create_market_data_provider(
    provider_name: str,
) -> MarketDataProvider:
    normalized_name = provider_name.strip().lower()

    if normalized_name in {"mock", "stub"}:
        return MockMarketDataProvider()

    if normalized_name in {"yfinance", "yahoo"}:
        return YFinanceMarketDataProvider()

    raise UnsupportedProviderError(f"Unsupported market-data provider: {provider_name}")
