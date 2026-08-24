from finai.core.config import (
    get_settings,
)
from finai.domain.execution.alpaca_market_guard import (
    AlpacaMarketGuard,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaPaperClient,
)


def main() -> None:
    settings = get_settings()

    client = AlpacaPaperClient(
        api_key=(
            settings.alpaca_api_key
        ),
        secret_key=(
            settings.alpaca_secret_key
        ),
        base_url=(
            settings.alpaca_base_url
        ),
        timeout_seconds=(
            settings
            .alpaca_request_timeout_seconds
        ),
    )

    asset = client.get_asset(
        symbol="AAPL"
    )

    clock = client.get_clock()

    guard = AlpacaMarketGuard(
        require_active_asset=(
            settings
            .alpaca_market_guard_require_active_asset
        ),
        require_tradable_asset=(
            settings
            .alpaca_market_guard_require_tradable_asset
        ),
        require_market_open=False,
        require_fractionable=(
            settings
            .alpaca_market_guard_require_fractionable
        ),
    )

    result = (
        guard.validate_order(
            asset=asset,
            clock=clock,
            symbol="AAPL",
            quantity=1.0,
        )
    )

    print(
        "Version 2.6 Alpaca "
        "market guard passed."
    )

    print(
        "Symbol:",
        result.symbol,
    )

    print(
        "Asset status:",
        result.asset_status,
    )

    print(
        "Tradable:",
        result.tradable,
    )

    print(
        "Fractionable:",
        result.fractionable,
    )

    print(
        "Market open:",
        result.market_open,
    )

    print(
        "Timestamp:",
        result.clock_timestamp,
    )

    print(
        "Next open:",
        result.next_open,
    )

    print(
        "Next close:",
        result.next_close,
    )

    if (
        settings
        .alpaca_market_guard_require_market_open
        and not result.market_open
    ):
        print(
            "Live order submission "
            "would currently be blocked "
            "because the market is closed."
        )


if __name__ == "__main__":
    main()