from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TradingControlState:
    trading_enabled: bool
    kill_switch_active: bool
    reason: str | None

    @property
    def can_trade(self) -> bool:
        return self.trading_enabled and not self.kill_switch_active


def validate_trading_control(
    *,
    trading_enabled: bool,
    kill_switch_active: bool,
    reason: str | None,
) -> None:
    if kill_switch_active and not reason:
        raise ValueError("A kill-switch reason is required.")

    if reason is not None and not reason.strip():
        raise ValueError("Trading-control reason cannot be blank.")

    if kill_switch_active and trading_enabled:
        raise ValueError("Trading cannot be enabled while the kill switch is active.")
