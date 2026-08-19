from datetime import UTC, datetime, timedelta

from finai.domain.strategy.schedule_enums import (
    StrategyScheduleFrequency,
)


def ensure_utc(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def calculate_next_run_at(
    *,
    frequency: StrategyScheduleFrequency,
    from_time: datetime,
) -> datetime:
    normalized_time = ensure_utc(from_time)

    if frequency == StrategyScheduleFrequency.HOURLY:
        return normalized_time + timedelta(hours=1)

    if frequency == StrategyScheduleFrequency.DAILY:
        return normalized_time + timedelta(days=1)

    raise ValueError(
        f"Unsupported schedule frequency: {frequency}"
    )


def is_schedule_due(
    *,
    enabled: bool,
    next_run_at: datetime | None,
    now: datetime,
) -> bool:
    if not enabled:
        return False

    if next_run_at is None:
        return True

    normalized_now = ensure_utc(now)
    normalized_next_run = ensure_utc(next_run_at)

    return normalized_next_run <= normalized_now