from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(
    frozen=True,
    slots=True,
)
class V37JobStatus:
    name: str

    last_started_at: datetime | None
    last_completed_at: datetime | None

    last_success: bool | None

    consecutive_failures: int

    last_error: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class V37PlatformHealth:
    timestamp: datetime

    healthy: bool

    execution_mode: str

    live_money_enabled: bool

    kill_switch_active: bool

    latest_market_timestamp: datetime | None

    market_data_age_seconds: float | None

    market_data_status: str

    champion_exists: bool

    total_market_bars: int

    message: str
