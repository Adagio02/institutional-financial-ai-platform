from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(
    frozen=True,
    slots=True,
)
class V36ExecutionDecision:
    decision_id: str

    symbol: str
    interval: str

    timestamp: datetime

    signal: str
    confidence: float

    reference_price: float

    quantity: float

    should_execute: bool
    reason: str


@dataclass(
    frozen=True,
    slots=True,
)
class V36ExecutionResult:
    decision_id: str

    client_order_id: str

    symbol: str
    side: str

    quantity: float

    submitted_at: datetime

    accepted: bool

    order_id: str | None
    broker_order_id: str | None
    status: str | None

    error: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class V36Outcome:
    decision_id: str

    symbol: str
    side: str

    entry_timestamp: datetime
    outcome_timestamp: datetime

    entry_price: float
    outcome_price: float

    gross_return: float

    correct_direction: bool