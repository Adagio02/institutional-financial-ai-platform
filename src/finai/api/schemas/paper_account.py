from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class PaperAccountCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=128,
    )

    initial_cash: float = Field(
        default=100_000.0,
        gt=0,
    )

    base_currency: str = Field(
        default="USD",
        min_length=3,
        max_length=8,
    )


class PaperAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    base_currency: str
    initial_cash: float
    cash: float
    realized_pnl: float
    created_at: datetime
