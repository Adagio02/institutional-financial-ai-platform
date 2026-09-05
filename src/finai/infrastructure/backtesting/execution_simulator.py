from finai.domain.backtesting.enums import (
    TradeSide,
)


def apply_slippage(
    *,
    price: float,
    side: TradeSide,
    slippage_bps: float,
) -> float:
    slippage_fraction = slippage_bps / 10_000

    if side == TradeSide.BUY:
        return price * (1.0 + slippage_fraction)

    return price * (1.0 - slippage_fraction)


def calculate_transaction_cost(
    *,
    notional: float,
    commission_bps: float,
) -> float:
    return abs(notional) * (commission_bps / 10_000)
