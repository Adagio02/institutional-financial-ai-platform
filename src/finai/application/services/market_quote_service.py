from __future__ import annotations

from sqlalchemy.orm import Session

from finai.core.config import (
    get_settings,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.market_data.quote import (
    MarketQuote,
)
from finai.infrastructure.market_data.alpaca_market_data_client import (
    AlpacaMarketDataClient,
)
from finai.infrastructure.market_data.alpaca_quote_provider import (
    AlpacaQuoteProvider,
)
from finai.infrastructure.market_data.persisted_quote_provider import (
    PersistedQuoteProvider,
)


class MarketQuoteService:
    def __init__(
        self,
        *,
        session: Session,
        maximum_quote_age_seconds: int,
        quote_interval: BarInterval,
        synthetic_spread_bps: float,
        execution_mode: str = "paper",
    ) -> None:
        normalized_execution_mode = (
            execution_mode
            .strip()
            .lower()
        )

        if normalized_execution_mode not in {
            "paper",
            "sandbox",
            "alpaca_paper",
        }:
            raise ValueError(
                "Unsupported execution mode: "
                f"{execution_mode}"
            )

        if (
            normalized_execution_mode
            == "alpaca_paper"
        ):
            settings = get_settings()

            client = (
                AlpacaMarketDataClient(
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
            )

            self._provider = (
                AlpacaQuoteProvider(
                    client=client
                )
            )

        else:
            self._provider = (
                PersistedQuoteProvider(
                    session=session,
                    interval=quote_interval,
                    maximum_age_seconds=(
                        maximum_quote_age_seconds
                    ),
                    synthetic_spread_bps=(
                        synthetic_spread_bps
                    ),
                )
            )

    def get_quote(
        self,
        *,
        symbol: str,
    ) -> MarketQuote:
        return (
            self._provider
            .get_quote(
                symbol=symbol
            )
        )