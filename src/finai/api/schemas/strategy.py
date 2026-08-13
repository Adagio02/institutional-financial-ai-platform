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


class TradeProposalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID

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


class ProposalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(
        default=None,
        max_length=1024,
    )


class ProposalRejectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        min_length=1,
        max_length=1024,
    )


class TradeProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    account_id: UUID
    instrument_id: UUID

    order_id: UUID | None

    source_model_id: UUID | None
    source_prediction_id: UUID | None

    symbol: str
    side: str

    confidence: float

    quantity: float
    proposed_notional: float
    allocation_fraction: float

    reference_price: float

    reference_price_timestamp: datetime

    reference_price_provider: str

    status: str

    rejection_reason: str | None
    decision_reason: str | None

    approved_at: datetime | None
    rejected_at: datetime | None
    executed_at: datetime | None

    created_at: datetime
    updated_at: datetime
