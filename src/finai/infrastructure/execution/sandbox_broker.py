from datetime import (
    UTC,
    datetime,
)
from uuid import UUID

from finai.domain.execution.broker import (
    BrokerExecutionResult,
    BrokerFill,
    BrokerOrderState,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)
from finai.infrastructure.execution.execution_price import (
    apply_execution_slippage,
    calculate_commission,
)


class SandboxBroker:
    def __init__(
        self,
        *,
        commission_bps: float,
        slippage_bps: float,
        partial_fill_enabled: bool,
        initial_fill_fraction: float,
    ) -> None:
        if not 0 < initial_fill_fraction <= 1:
            raise ValueError("initial_fill_fraction must be greater than zero and at most one.")

        self._commission_bps = commission_bps

        self._slippage_bps = slippage_bps

        self._partial_fill_enabled = partial_fill_enabled

        self._initial_fill_fraction = initial_fill_fraction

    @property
    def name(self) -> str:
        return "sandbox"

    def submit(
        self,
        *,
        order_id: UUID,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        reference_price: float,
        limit_price: float | None,
    ) -> BrokerExecutionResult:
        del symbol

        if quantity <= 0:
            raise ValueError("Order quantity must be positive.")

        execution_price = apply_execution_slippage(
            reference_price=(reference_price),
            side=side,
            slippage_bps=(self._slippage_bps),
        )

        if order_type == OrderType.LIMIT:
            if limit_price is None:
                raise ValueError("Limit orders require limit_price.")

            if side == OrderSide.BUY and execution_price > limit_price:
                return BrokerExecutionResult(
                    broker_order_id=(f"sandbox-{order_id}"),
                    status=(OrderStatus.ACCEPTED),
                    requested_quantity=quantity,
                    filled_quantity=0.0,
                    fills=(),
                )

            if side == OrderSide.SELL and execution_price < limit_price:
                return BrokerExecutionResult(
                    broker_order_id=(f"sandbox-{order_id}"),
                    status=(OrderStatus.ACCEPTED),
                    requested_quantity=quantity,
                    filled_quantity=0.0,
                    fills=(),
                )

        if self._partial_fill_enabled:
            fill_quantity = quantity * self._initial_fill_fraction
        else:
            fill_quantity = quantity

        fill_quantity = min(
            fill_quantity,
            quantity,
        )

        notional = fill_quantity * execution_price

        commission = calculate_commission(
            notional=notional,
            commission_bps=(self._commission_bps),
        )

        raw_notional = fill_quantity * reference_price

        slippage_cost = abs(notional - raw_notional)

        fill = BrokerFill(
            quantity=fill_quantity,
            price=execution_price,
            commission=commission,
            slippage_cost=(slippage_cost),
        )

        if fill_quantity >= quantity:
            status = OrderStatus.FILLED
        else:
            status = OrderStatus.PARTIALLY_FILLED

        return BrokerExecutionResult(
            broker_order_id=(f"sandbox-{order_id}"),
            status=status,
            requested_quantity=quantity,
            filled_quantity=(fill_quantity),
            fills=(fill,),
        )

    def cancel(
        self,
        *,
        broker_order_id: str,
    ) -> BrokerOrderState:
        if not broker_order_id:
            raise ValueError("broker_order_id is required.")

        return BrokerOrderState(
            broker_order_id=(broker_order_id),
            status=(OrderStatus.CANCELLED),
            requested_quantity=0.0,
            filled_quantity=0.0,
            updated_at=datetime.now(UTC),
        )
