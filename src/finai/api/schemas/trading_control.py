from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class TradingControlResponse(BaseModel):
    trading_enabled: bool
    kill_switch_active: bool
    reason: str | None
    can_trade: bool


class TradingEnabledUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool

    reason: str | None = Field(
        default=None,
        max_length=512,
    )


class KillSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        min_length=1,
        max_length=512,
    )
