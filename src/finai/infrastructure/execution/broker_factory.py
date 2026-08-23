from finai.core.config import (
    Settings,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaPaperClient,
)
from finai.infrastructure.execution.sandbox_broker import (
    SandboxBroker,
)


def create_execution_broker(
    *,
    settings: Settings,
):
    mode = (
        settings.execution_mode
        .strip()
        .lower()
    )

    if mode == "sandbox":
        return SandboxBroker(
            commission_bps=(
                settings
                .paper_trading_commission_bps
            ),
            slippage_bps=(
                settings
                .paper_trading_slippage_bps
            ),
            partial_fill_enabled=(
                settings
                .sandbox_partial_fill_enabled
            ),
            initial_fill_fraction=(
                settings
                .sandbox_initial_fill_fraction
            ),
        )

    if mode == "alpaca_paper":
        if not (
            settings
            .alpaca_paper_trading_enabled
        ):
            raise ValueError(
                "Alpaca paper integration "
                "is disabled."
            )

        if not (
            settings
            .alpaca_execution_enabled
        ):
            raise ValueError(
                "Alpaca external execution "
                "is disabled."
            )

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

        return AlpacaPaperBroker(
            client=client
        )

    raise ValueError(
        "External broker requires "
        "execution_mode='sandbox' or "
        "'alpaca_paper'."
    )