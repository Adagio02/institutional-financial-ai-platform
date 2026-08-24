from __future__ import annotations

from finai.core.config import (
    Settings,
)
from finai.domain.execution.alpaca_account_guard import (
    AlpacaAccountGuard,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaPaperClient,
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

    return AlpacaPaperBroker(
        client=client,
        account_guard=(
            account_guard
        ),
    )