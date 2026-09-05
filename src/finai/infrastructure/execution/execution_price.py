from finai.domain.execution.enums import (
    OrderSide,
)


def apply_execution_slippage(
    *,
    reference_price: float,
    side: OrderSide,
    slippage_bps: float,
) -> float:
    if reference_price <= 0:
        raise ValueError("reference_price must be positive.")

    if slippage_bps < 0:
        raise ValueError("slippage_bps cannot be negative.")

    slippage = slippage_bps / 10_000

    if side == OrderSide.BUY:
        return reference_price * (1 + slippage)

    return reference_price * (1 - slippage)


def calculate_commission(
    *,
    notional: float,
    commission_bps: float,
) -> float:
    if commission_bps < 0:
        raise ValueError("commission_bps cannot be negative.")

    return abs(notional) * (commission_bps / 10_000)
