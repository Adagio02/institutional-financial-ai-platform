from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class StrategyPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True

    allow_buy: bool = True
    allow_sell: bool = True

    capital_budget_fraction: float = Field(
        gt=0,
        le=1,
    )

    maximum_single_proposal_fraction: float = Field(
        gt=0,
        le=1,
    )

    maximum_gross_exposure_fraction: float = Field(
        gt=0,
    )

    maximum_symbol_fraction: float = Field(
        gt=0,
        le=1,
    )

    maximum_daily_loss: float = Field(
        gt=0,
    )

    cooldown_seconds: int = Field(
        ge=0,
    )

    maximum_active_proposals: int = Field(
        ge=1,
    )


class StrategyPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    account_id: UUID
    strategy_key: str

    enabled: bool

    allow_buy: bool
    allow_sell: bool

    capital_budget_fraction: float

    maximum_single_proposal_fraction: float

    maximum_gross_exposure_fraction: float

    maximum_symbol_fraction: float

    maximum_daily_loss: float

    cooldown_seconds: int

    maximum_active_proposals: int

    created_at: datetime
    updated_at: datetime


class StrategyPerformanceResponse(BaseModel):
    account_id: UUID
    strategy_key: str

    daily_net_pnl: float

    gross_book_exposure: float

    position_count: int
