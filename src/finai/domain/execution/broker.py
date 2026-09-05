from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)


@dataclass(frozen=True, slots=True)
class BrokerFill:
    quantity: float
    price: float
    commission: float
    slippage_cost: float


@dataclass(frozen=True, slots=True)
class BrokerExecutionResult:
    broker_order_id: str

    status: OrderStatus

    requested_quantity: float
    filled_quantity: float

    fills: tuple[
        BrokerFill,
        ...,
    ]


@dataclass(frozen=True, slots=True)
class BrokerOrderState:
    broker_order_id: str

    status: OrderStatus

    requested_quantity: float
    filled_quantity: float

    updated_at: datetime


class BrokerAdapter(Protocol):
    @property
    def name(self) -> str: ...

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
    ) -> BrokerExecutionResult: ...

    def cancel(
        self,
        *,
        broker_order_id: str,
    ) -> BrokerOrderState: ...
