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
)
from finai.domain.strategy.schedule_enums import (
    StrategyScheduleFrequency,
)


class StrategyScheduleSignalCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    symbol: str = Field(
        min_length=1,
        max_length=32,
    )

    side: OrderSide

    confidence: float = Field(
        ge=0,
        le=1,
    )

    source_model_id: UUID | None = None
    source_prediction_id: UUID | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError(
                "symbol cannot be blank"
            )

        return normalized


class StrategyScheduleCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    account_id: UUID

    strategy_key: str = Field(
        default="default",
        min_length=1,
        max_length=128,
    )

    name: str = Field(
        min_length=1,
        max_length=128,
    )

    frequency: StrategyScheduleFrequency

    enabled: bool = True

    signals: list[
        StrategyScheduleSignalCreate
    ] = Field(
        min_length=1,
    )


class StrategyScheduleSignalResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    schedule_id: UUID
    sequence_number: int
    symbol: str
    side: str
    confidence: float
    source_model_id: UUID | None
    source_prediction_id: UUID | None
    created_at: datetime


class StrategyScheduleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    account_id: UUID
    strategy_key: str
    name: str
    frequency: str
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StrategyScheduleDetailResponse(
    StrategyScheduleResponse
):
    signals: list[
        StrategyScheduleSignalResponse
    ]