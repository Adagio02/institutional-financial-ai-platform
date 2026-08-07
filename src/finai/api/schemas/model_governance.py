from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelCardCreate(BaseModel):
    summary: str = Field(
        min_length=1,
        max_length=4000,
    )

    intended_use: str = Field(
        min_length=1,
        max_length=4000,
    )

    limitations: str = Field(
        min_length=1,
        max_length=4000,
    )


class ModelCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: UUID
    summary: str
    intended_use: str
    limitations: str
    evaluation_summary: dict[str, Any]
    governance_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProductionEvaluationResponse(BaseModel):
    model_id: UUID
    approved: bool
    metrics: dict[str, float]
    artifact_verified: bool
    model_card_present: bool
