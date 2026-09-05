from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class PredictionCreate(BaseModel):
    model_id: UUID
    dataset_id: UUID

    symbol: str = Field(
        min_length=1,
        max_length=32,
    )

    prediction_timestamp: datetime | None = None

    forecast_horizon: str = Field(
        default="next_period",
        min_length=1,
        max_length=32,
    )

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


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: UUID
    dataset_id: UUID
    instrument_id: UUID
    symbol: str
    prediction_timestamp: datetime
    forecast_horizon: str
    raw_prediction: float
    probability: float | None
    confidence: float | None
    feature_values: dict[str, float]
    model_hash: str
    status: str
    error_message: str | None
    created_at: datetime
