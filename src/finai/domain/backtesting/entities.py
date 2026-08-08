from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BacktestConfiguration:
    model_id: UUID
    dataset_id: UUID

    initial_capital: float

    long_threshold: float
    short_threshold: float

    position_size_fraction: float

    commission_bps: float
    slippage_bps: float

    allow_short: bool


@dataclass(frozen=True, slots=True)
class TradeExecution:
    timestamp: datetime
    side: str
    quantity: float
    price: float
    transaction_cost: float
    realized_pnl: float


@dataclass(frozen=True, slots=True)
class PortfolioState:
    timestamp: datetime
    cash: float
    position_quantity: float
    market_value: float
    equity: float
    drawdown: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    backtest_run_id: UUID
    final_equity: float
    total_return: float
    maximum_drawdown: float
    sharpe_ratio: float | None
    trade_count: int
