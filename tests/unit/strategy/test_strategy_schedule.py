from datetime import (
    UTC,
    datetime,
    timedelta,
)

from finai.domain.strategy.schedule_calculator import (
    calculate_next_run_at,
    is_schedule_due,
)
from finai.domain.strategy.schedule_enums import (
    StrategyScheduleFrequency,
)


def test_hourly_schedule() -> None:
    now = datetime(
        2026,
        8,
        18,
        12,
        0,
        tzinfo=UTC,
    )

    result = calculate_next_run_at(
        frequency=StrategyScheduleFrequency.HOURLY,
        from_time=now,
    )

    assert result == now + timedelta(hours=1)


def test_daily_schedule() -> None:
    now = datetime(
        2026,
        8,
        18,
        12,
        0,
        tzinfo=UTC,
    )

    result = calculate_next_run_at(
        frequency=StrategyScheduleFrequency.DAILY,
        from_time=now,
    )

    assert result == now + timedelta(days=1)


def test_disabled_schedule_is_not_due() -> None:
    now = datetime.now(UTC)

    assert not is_schedule_due(
        enabled=False,
        next_run_at=now - timedelta(hours=1),
        now=now,
    )


def test_schedule_is_due() -> None:
    now = datetime.now(UTC)

    assert is_schedule_due(
        enabled=True,
        next_run_at=now - timedelta(seconds=1),
        now=now,
    )


def test_future_schedule_is_not_due() -> None:
    now = datetime.now(UTC)

    assert not is_schedule_due(
        enabled=True,
        next_run_at=now + timedelta(hours=1),
        now=now,
    )