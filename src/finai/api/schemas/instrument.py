from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from finai.domain.market_data.enums import AssetClass


class InstrumentCreateRequest(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=32,
        examples=["AAPL"],
    )

    name: str = Field(
        min_length=1,
        max_length=255,
        examples=["Apple Inc."],
    )

    asset_class: AssetClass

    exchange: str = Field(
        min_length=1,
        max_length=64,
        examples=["NASDAQ"],
    )

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("exchange", "currency")
    @classmethod
    def normalize_uppercase(cls, value: str) -> str:
        return value.strip().upper()


class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    instrument_id: UUID
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: str
    currency: str
    active: bool
