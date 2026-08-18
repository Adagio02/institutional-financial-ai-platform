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


class StrategyRunSignalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
            raise ValueError("symbol cannot be empty")

        return normalized


class StrategyRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID

    strategy_key: str = Field(
        default="default",
        min_length=1,
        max_length=128,
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=128,
    )

    signals: list[StrategyRunSignalCreate] = Field(
        min_length=1,
    )

    @field_validator(
        "strategy_key",
        "idempotency_key",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("value cannot be empty")

        return normalized


class StrategyRunItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    strategy_run_id: UUID

    sequence_number: int

    symbol: str
    side: str
    confidence: float

    source_model_id: UUID | None
    source_prediction_id: UUID | None

    proposal_id: UUID | None

    status: str

    error_message: str | None

    created_at: datetime
    completed_at: datetime | None


class StrategyRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    account_id: UUID
    strategy_key: str

    idempotency_key: str

    status: str

    signal_count: int
    proposal_count: int
    rejected_count: int
    failed_count: int

    error_message: str | None

    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class StrategyRunDetailResponse(StrategyRunResponse):
    items: list[StrategyRunItemResponse]
