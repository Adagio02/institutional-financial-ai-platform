from finai.core.config import (
    get_settings,
)
from finai.infrastructure.market_data.alpaca_market_data_client import (
    AlpacaMarketDataClient,
)


def main() -> None:
    settings = get_settings()

    client = AlpacaMarketDataClient(
        api_key=(
            settings.alpaca_api_key
        ),
        secret_key=(
            settings.alpaca_secret_key
        ),
        base_url=(
            settings
            .alpaca_data_base_url
        ),
        feed=(
            settings
            .alpaca_market_data_feed
        ),
        timeout_seconds=(
            settings
            .alpaca_request_timeout_seconds
        ),
    )

    quote = (
        client.get_latest_quote(
            symbol="AAPL"
        )
    )

    print(
        "Version 2.8 Alpaca "
        "latest-quote connection passed."
    )

    print(
        "Feed:",
        client.feed,
    )

    print(
        "Bid:",
        quote.get(
            "bp"
        ),
    )

    print(
        "Ask:",
        quote.get(
            "ap"
        ),
    )

    print(
        "Bid size:",
        quote.get(
            "bs"
        ),
    )

    print(
        "Ask size:",
        quote.get(
            "as"
        ),
    )

    print(
        "Timestamp:",
        quote.get(
            "t"
        ),
    )


if __name__ == "__main__":
    main()