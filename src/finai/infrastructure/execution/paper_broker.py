from dataclasses import dataclass

from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
)
from finai.infrastructure.execution.execution_price import (
    apply_execution_slippage,
    calculate_commission,
)


@dataclass(frozen=True, slots=True)
class PaperFill:
    quantity: float
    price: float
    notional: float
    commission: float
    slippage_cost: float


class PaperBroker:
    def __init__(
        self,
        *,
        commission_bps: float,
        slippage_bps: float,
    ) -> None:
        self._commission_bps = commission_bps
        self._slippage_bps = slippage_bps

    def execute(
        self,
        *,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        reference_price: float,
        limit_price: float | None,
    ) -> PaperFill | None:
        execution_price = apply_execution_slippage(
            reference_price=reference_price,
            side=side,
            slippage_bps=(self._slippage_bps),
        )

        if order_type == OrderType.LIMIT:
            if limit_price is None:
                raise ValueError("Limit order requires limit_price.")

            if side == OrderSide.BUY and execution_price > limit_price:
                return None

            if side == OrderSide.SELL and execution_price < limit_price:
                return None

        notional = quantity * execution_price

        commission = calculate_commission(
            notional=notional,
            commission_bps=(self._commission_bps),
        )

        raw_notional = quantity * reference_price

        slippage_cost = abs(notional - raw_notional)

        return PaperFill(
            quantity=quantity,
            price=execution_price,
            notional=notional,
            commission=commission,
            slippage_cost=slippage_cost,
        )
