from __future__ import annotations

from finai.core.config import (
    Settings,
)
from finai.domain.execution.alpaca_account_guard import (
    AlpacaAccountGuard,
)
from finai.domain.execution.alpaca_idempotency_guard import (
    AlpacaIdempotencyGuard,
)
from finai.domain.execution.alpaca_market_guard import (
    AlpacaMarketGuard,
)
from finai.domain.execution.alpaca_quote_guard import (
    AlpacaQuoteGuard,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaPaperClient,
)
from finai.infrastructure.market_data.alpaca_market_data_client import (
    AlpacaMarketDataClient,
)


def create_alpaca_paper_broker(
    *,
    settings: Settings,
) -> AlpacaPaperBroker:
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

    account_guard = None

    if (
        settings
        .alpaca_account_guard_enabled
    ):
        account_guard = (
            AlpacaAccountGuard(
                require_active=(
                    settings
                    .alpaca_account_guard_require_active
                ),
                maximum_buying_power_fraction=(
                    settings
                    .alpaca_account_guard_maximum_buying_power_fraction
                ),
                require_positive_buying_power=(
                    settings
                    .alpaca_account_guard_require_positive_buying_power
                ),
            )
        )

    market_guard = None

    if (
        settings
        .alpaca_market_guard_enabled
    ):
        market_guard = (
            AlpacaMarketGuard(
                require_active_asset=(
                    settings
                    .alpaca_market_guard_require_active_asset
                ),
                require_tradable_asset=(
                    settings
                    .alpaca_market_guard_require_tradable_asset
                ),
                require_market_open=(
                    settings
                    .alpaca_market_guard_require_market_open
                ),
                require_fractionable=(
                    settings
                    .alpaca_market_guard_require_fractionable
                ),
            )
        )

    idempotency_guard = None

    if (
        settings
        .alpaca_idempotency_guard_enabled
    ):
        idempotency_guard = (
            AlpacaIdempotencyGuard(
                require_order_match=(
                    settings
                    .alpaca_idempotency_require_order_match
                )
            )
        )

    market_data_client = None
    quote_guard = None

    if (
        settings
        .alpaca_quote_guard_enabled
    ):
        market_data_client = (
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

        quote_guard = (
            AlpacaQuoteGuard(
                maximum_age_seconds=(
                    settings
                    .alpaca_quote_guard_maximum_age_seconds
                ),
                maximum_spread_bps=(
                    settings
                    .alpaca_quote_guard_maximum_spread_bps
                ),
                maximum_reference_deviation_bps=(
                    settings
                    .alpaca_quote_guard_maximum_reference_deviation_bps
                ),
            )
        )

    return AlpacaPaperBroker(
        client=client,
        account_guard=(
            account_guard
        ),
        market_guard=(
            market_guard
        ),
        idempotency_guard=(
            idempotency_guard
        ),
        market_data_client=(
            market_data_client
        ),
        quote_guard=(
            quote_guard
        ),
        lookup_before_submit=(
            settings
            .alpaca_idempotency_lookup_before_submit
        ),
        recover_after_transport_error=(
            settings
            .alpaca_idempotency_recover_after_transport_error
        ),
    )