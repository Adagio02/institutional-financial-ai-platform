from dataclasses import dataclass
from enum import StrEnum


class TradingControlReason(StrEnum):
    MANUAL_HALT = "manual_halt"
    TRADING_DISABLED = "trading_disabled"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    GROSS_EXPOSURE_LIMIT = "gross_exposure_limit"
    SYMBOL_CONCENTRATION_LIMIT = "symbol_concentration_limit"
    ORDER_NOTIONAL_LIMIT = "order_notional_limit"


@dataclass(
    frozen=True,
    slots=True,
)
class TradingControlDecision:
    approved: bool
    reason: TradingControlReason | None
    message: str | None


def evaluate_trading_controls(
    *,
    trading_enabled: bool,
    manual_halt: bool,
    circuit_breaker_tripped: bool,
    account_equity: float,
    day_start_equity: float,
    current_gross_exposure: float,
    current_symbol_exposure: float,
    proposed_order_notional: float,
    maximum_daily_loss_fraction: float,
    maximum_gross_exposure_fraction: float,
    maximum_symbol_fraction: float,
    maximum_order_fraction: float,
) -> TradingControlDecision:
    if account_equity <= 0:
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason.TRADING_DISABLED
            ),
            message=(
                "Account equity must be greater "
                "than zero."
            ),
        )

    if not trading_enabled:
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason.TRADING_DISABLED
            ),
            message="Trading is disabled.",
        )

    if manual_halt:
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason.MANUAL_HALT
            ),
            message=(
                "Account trading is manually halted."
            ),
        )

    if circuit_breaker_tripped:
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason.TRADING_DISABLED
            ),
            message=(
                "Account circuit breaker is tripped."
            ),
        )

    daily_loss = max(
        day_start_equity - account_equity,
        0.0,
    )

    maximum_daily_loss = (
        day_start_equity
        * maximum_daily_loss_fraction
    )

    if daily_loss > maximum_daily_loss:
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason
                .DAILY_LOSS_LIMIT
            ),
            message=(
                "Maximum daily loss limit exceeded."
            ),
        )

    projected_gross_exposure = (
        current_gross_exposure
        + abs(proposed_order_notional)
    )

    maximum_gross_exposure = (
        account_equity
        * maximum_gross_exposure_fraction
    )

    if (
        projected_gross_exposure
        > maximum_gross_exposure
    ):
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason
                .GROSS_EXPOSURE_LIMIT
            ),
            message=(
                "Maximum gross exposure limit exceeded."
            ),
        )

    projected_symbol_exposure = (
        current_symbol_exposure
        + abs(proposed_order_notional)
    )

    maximum_symbol_exposure = (
        account_equity
        * maximum_symbol_fraction
    )

    if (
        projected_symbol_exposure
        > maximum_symbol_exposure
    ):
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason
                .SYMBOL_CONCENTRATION_LIMIT
            ),
            message=(
                "Maximum symbol concentration "
                "limit exceeded."
            ),
        )

    maximum_order_notional = (
        account_equity
        * maximum_order_fraction
    )

    if (
        abs(proposed_order_notional)
        > maximum_order_notional
    ):
        return TradingControlDecision(
            approved=False,
            reason=(
                TradingControlReason
                .ORDER_NOTIONAL_LIMIT
            ),
            message=(
                "Maximum order notional limit exceeded."
            ),
        )

    return TradingControlDecision(
        approved=True,
        reason=None,
        message=None,
    )