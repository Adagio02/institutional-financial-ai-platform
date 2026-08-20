from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class TradingControlResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    account_id: UUID

    trading_enabled: bool

    manual_halt: bool
    manual_halt_reason: str | None

    circuit_breaker_tripped: bool
    circuit_breaker_reason: str | None
    circuit_breaker_message: str | None

    circuit_breaker_tripped_at: (
        datetime | None
    )

    day_start_date: date | None
    day_start_equity: float | None

    maximum_daily_loss_fraction: float
    maximum_gross_exposure_fraction: float
    maximum_symbol_fraction: float
    maximum_order_fraction: float

    created_at: datetime
    updated_at: datetime


class TradingHaltRequest(BaseModel):
    reason: str = Field(
        min_length=1,
        max_length=1000,
    )


class TradingEnabledRequest(BaseModel):
    enabled: bool