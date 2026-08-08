from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class BacktestCreate(BaseModel):
    model_id: UUID
    dataset_id: UUID

    symbol: str = Field(
        min_length=1,
        max_length=32,
    )

    initial_capital: float = Field(
        default=100_000.0,
        gt=0,
    )

    long_threshold: float = 0.60
    short_threshold: float = 0.40

    position_size_fraction: float = Field(
        default=0.10,
        gt=0,
        le=1,
    )

    commission_bps: float = Field(
        default=1.0,
        ge=0,
    )

    slippage_bps: float = Field(
        default=2.0,
        ge=0,
    )

    allow_short: bool = False

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("symbol cannot be empty")

        return normalized

    @model_validator(mode="after")
    def validate_thresholds(
        self,
    ) -> "BacktestCreate":
        if self.short_threshold >= self.long_threshold:
            raise ValueError("short_threshold must be lower than long_threshold.")

        return self


class BacktestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: UUID
    dataset_id: UUID
    symbol: str

    initial_capital: float

    final_equity: float | None
    total_return: float | None
    maximum_drawdown: float | None
    sharpe_ratio: float | None

    trade_count: int

    configuration: dict[str, Any]
    metrics: dict[str, Any]

    status: str
    error_message: str | None

    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class SimulatedTradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    backtest_run_id: UUID
    timestamp: datetime

    side: str
    quantity: float
    execution_price: float
    notional: float
    transaction_cost: float
    realized_pnl: float

    created_at: datetime


class PortfolioSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    backtest_run_id: UUID
    timestamp: datetime

    cash: float
    position_quantity: float
    market_price: float
    market_value: float
    equity: float
    drawdown: float

    created_at: datetime
