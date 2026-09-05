import asyncio

from finai.core.config import (
    get_settings,
)
from finai.infrastructure.execution.alpaca_trade_update_stream import (
    ALPACA_PAPER_STREAM_URL,
    AlpacaTradeUpdateStream,
)


async def verify() -> None:
    settings = get_settings()

    if (
        settings.alpaca_trade_stream_url
        != ALPACA_PAPER_STREAM_URL
    ):
        raise RuntimeError(
            "Version 2.1 requires "
            "the Alpaca paper "
            "WebSocket endpoint."
        )

    stream = (
        AlpacaTradeUpdateStream(
            api_key=(
                settings.alpaca_api_key
            ),
            secret_key=(
                settings
                .alpaca_secret_key
            ),
            stream_url=(
                settings
                .alpaca_trade_stream_url
            ),
            open_timeout_seconds=(
                settings
                .alpaca_trade_stream_open_timeout_seconds
            ),
        )
    )

    await asyncio.wait_for(
        stream.verify_connection(),
        timeout=20.0,
    )

    print(
        "Version 2.1 Alpaca "
        "trade-update stream passed."
    )


def main() -> None:
    asyncio.run(
        verify()
    )


if __name__ == "__main__":
    main()