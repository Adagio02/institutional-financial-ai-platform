from typing import Any
from uuid import UUID

from pydantic import BaseModel


class PositionResponse(BaseModel):
    instrument_id: UUID
    symbol: str

    quantity: float
    average_price: float

    market_price: float
    market_value: float

    unrealized_pnl: float


class PortfolioResponse(BaseModel):
    account_id: UUID

    cash: float

    gross_exposure: float
    net_exposure: float

    equity: float

    realized_pnl: float
    unrealized_pnl: float

    positions: list[dict[str, Any]]
