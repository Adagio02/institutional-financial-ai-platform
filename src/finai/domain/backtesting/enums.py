from enum import StrEnum


class BacktestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SignalDirection(StrEnum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class PositionSizingMethod(StrEnum):
    FIXED_FRACTION = "fixed_fraction"
    FIXED_NOTIONAL = "fixed_notional"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
