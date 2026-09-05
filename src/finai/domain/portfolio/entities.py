from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PositionState:
    instrument_id: UUID
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    account_id: UUID
    cash: float
    gross_exposure: float
    net_exposure: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
