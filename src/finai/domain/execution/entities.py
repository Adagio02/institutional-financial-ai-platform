from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OrderRequest:
    account_id: UUID
    instrument_id: UUID
    symbol: str
    side: str
    order_type: str
    quantity: float
    limit_price: float | None
    time_in_force: str


@dataclass(frozen=True, slots=True)
class FillResult:
    order_id: UUID
    timestamp: datetime
    quantity: float
    price: float
    notional: float
    commission: float
    slippage_cost: float


@dataclass(frozen=True, slots=True)
class OrderRiskDecision:
    approved: bool
    reason: str | None
    requested_notional: float
    projected_gross_exposure: float
