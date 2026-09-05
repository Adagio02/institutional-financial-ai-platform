from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pytest

from finai.domain.strategy.schedule_retry import (
    calculate_retry_at,
    calculate_retry_delay_seconds,
)


def test_first_failure_uses_base_delay() -> None:
    result = calculate_retry_delay_seconds(
        failure_count=1,
        base_delay_seconds=60,
        maximum_delay_seconds=3600,
    )

    assert result == 60


def test_retry_delay_uses_exponential_backoff() -> None:
    result = calculate_retry_delay_seconds(
        failure_count=4,
        base_delay_seconds=60,
        maximum_delay_seconds=3600,
    )

    assert result == 480


def test_retry_delay_is_capped() -> None:
    result = calculate_retry_delay_seconds(
        failure_count=10,
        base_delay_seconds=60,
        maximum_delay_seconds=3600,
    )

    assert result == 3600


def test_retry_at_adds_delay() -> None:
    now = datetime(
        2026,
        8,
        18,
        12,
        0,
        tzinfo=UTC,
    )

    result = calculate_retry_at(
        now=now,
        failure_count=2,
        base_delay_seconds=60,
        maximum_delay_seconds=3600,
    )

    assert result == (
        now + timedelta(seconds=120)
    )


def test_invalid_failure_count_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="failure_count",
    ):
        calculate_retry_delay_seconds(
            failure_count=0,
            base_delay_seconds=60,
            maximum_delay_seconds=3600,
        )