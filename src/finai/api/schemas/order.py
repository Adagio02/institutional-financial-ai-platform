from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
    TimeInForce,
)


class OrderCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    account_id: UUID

    symbol: str = Field(
        min_length=1,
        max_length=32,
    )

    side: OrderSide

    order_type: OrderType = (
        OrderType.MARKET
    )

    quantity: float = Field(
        gt=0,
    )

    limit_price: float | None = Field(
        default=None,
        gt=0,
    )

    time_in_force: TimeInForce = (
        TimeInForce.DAY
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError(
                "symbol cannot be empty"
            )

        return normalized


class OrderResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    account_id: UUID
    instrument_id: UUID
    symbol: str

    side: str
    order_type: str

    quantity: float
    filled_quantity: float

    limit_price: float | None
    average_fill_price: float | None

    reference_price: float | None
    reference_price_timestamp: datetime | None
    reference_price_provider: str | None

    time_in_force: str
    status: str

    rejection_reason: str | None

    created_at: datetime
    updated_at: datetime


class FillResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    order_id: UUID

    quantity: float
    price: float
    notional: float

    commission: float
    slippage_cost: float

    executed_at: datetime