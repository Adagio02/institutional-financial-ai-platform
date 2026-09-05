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

from finai.domain.market_data.enums import (
    BarInterval,
)


class FeatureGenerationRequest(BaseModel):
    feature_set_name: str = Field(
        min_length=1,
        max_length=128,
    )

    description: str | None = None

    symbol: str = Field(
        min_length=1,
        max_length=32,
    )

    interval: BarInterval
    start_time: datetime
    end_time: datetime
    configuration: dict[str, Any]

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
    def validate_time_range(
        self,
    ) -> "FeatureGenerationRequest":
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")

        if self.end_time.tzinfo is None:
            raise ValueError("end_time must be timezone-aware")

        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")

        return self


class FeatureGenerationResponse(BaseModel):
    feature_set_id: UUID
    name: str
    version: int
    values_persisted: int


class FeatureSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    version: int
    configuration: dict[str, Any]
    created_at: datetime
