from __future__ import annotations

from dataclasses import (
    dataclass,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PreTradeRiskRequest:
    symbol: str
    side: str

    quantity: float
    reference_price: float

    current_position_quantity: float = 0.0

    buying_power: float | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class PreTradeRiskDecision:
    approved: bool

    reason: str | None

    symbol: str
    side: str

    quantity: float
    reference_price: float

    order_notional: float
    projected_position_quantity: float
    projected_position_notional: float