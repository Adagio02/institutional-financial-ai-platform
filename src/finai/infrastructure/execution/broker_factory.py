from __future__ import annotations

from finai.core.config import (
    Settings,
)
from finai.infrastructure.execution.alpaca_broker_factory import (
    create_alpaca_paper_broker,
)
from finai.infrastructure.execution.sandbox_broker import (
    SandboxBroker,
)


def create_execution_broker(
    *,
    settings: Settings,
):
    execution_mode = (
        settings.execution_mode
        .strip()
        .lower()
    )

    if execution_mode == "sandbox":
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

    if execution_mode == "alpaca_paper":
        if not (
            settings
            .alpaca_paper_trading_enabled
        ):
            raise ValueError(
                "Alpaca paper trading "
                "is disabled."
            )

        if not (
            settings
            .alpaca_execution_enabled
        ):
            raise ValueError(
                "Alpaca execution "
                "is disabled."
            )

        return (
            create_alpaca_paper_broker(
                settings=settings
            )
        )

    raise ValueError(
        "Unsupported execution mode: "
        f"{settings.execution_mode}"
    )