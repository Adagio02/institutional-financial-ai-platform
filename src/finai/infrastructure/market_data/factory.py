from finai.infrastructure.market_data.mock_provider import (
    MockMarketDataProvider,
)


def create_market_data_provider(
    provider_name: str,
) -> MockMarketDataProvider:
    normalized_name = provider_name.strip().lower()

    if normalized_name in {"mock", "stub"}:
        return MockMarketDataProvider()

    raise ValueError(
        f"Unsupported market-data provider: {provider_name}"
    )