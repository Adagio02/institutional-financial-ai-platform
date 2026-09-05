from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class DatasetBuildRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=128,
    )

    feature_set_id: UUID

    symbol: str = Field(
        min_length=1,
        max_length=32,
    )

    interval: str = Field(
        min_length=1,
        max_length=16,
    )

    start_time: datetime
    end_time: datetime
    drop_missing_rows: bool = True

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
    ) -> "DatasetBuildRequest":
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")

        if self.end_time.tzinfo is None:
            raise ValueError("end_time must be timezone-aware")

        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")

        return self


class DatasetBuildResponse(BaseModel):
    dataset_id: UUID
    name: str
    version: int
    row_count: int
    schema_hash: str
    content_hash: str
    storage_uri: str


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: int
    feature_set_id: UUID
    symbol: str
    interval: str
    start_time: datetime
    end_time: datetime
    row_count: int
    schema_hash: str | None
    content_hash: str | None
    storage_uri: str | None
    status: str
    configuration: dict
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
