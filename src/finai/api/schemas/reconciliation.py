from uuid import UUID

from pydantic import BaseModel


class PositionReconciliationItem(BaseModel):
    instrument_id: UUID
    symbol: str
    quantity: float
    average_price: float

    issue: str | None


class AccountReconciliationResponse(BaseModel):
    account_id: UUID

    cash: float
    realized_pnl: float

    position_count: int
    issue_count: int

    healthy: bool

    positions: list[PositionReconciliationItem]
