from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from finai.domain.market_data.enums import BarInterval


class MarketDataIngestionRequest(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=32,
        examples=["AAPL"],
    )

    interval: BarInterval

    start_time: datetime

    end_time: datetime

    @model_validator(mode="after")
    def validate_time_range(
        self,
    ) -> "MarketDataIngestionRequest":
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must include a timezone.")

        if self.end_time.tzinfo is None:
            raise ValueError("end_time must include a timezone.")

        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time.")

        return self


class MarketDataIngestionResponse(BaseModel):
    symbol: str
    interval: BarInterval
    provider: str
    bars_received: int
    bars_persisted: int
    start_time: datetime
    end_time: datetime


class MarketBarResponse(BaseModel):
    symbol: str
    interval: BarInterval
    timestamp: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    provider: str


class MarketBarCollectionResponse(BaseModel):
    symbol: str
    interval: BarInterval
    count: int
    bars: list[MarketBarResponse]
