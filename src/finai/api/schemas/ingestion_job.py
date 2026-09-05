from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from finai.domain.market_data.enums import BarInterval


class IngestionJobCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    interval: BarInterval
    start_time: datetime
    end_time: datetime

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("symbol cannot be empty")

        return normalized

    @model_validator(mode="after")
    def validate_time_range(self) -> "IngestionJobCreate":
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must include a timezone")

        if self.end_time.tzinfo is None:
            raise ValueError("end_time must include a timezone")

        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")

        return self


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    interval: str
    start_time: datetime
    end_time: datetime
    status: str
    received_count: int
    inserted_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
