from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pytest

from finai.domain.strategy.worker_health import (
    is_worker_stale,
    validate_heartbeat_interval,
    validate_poll_interval,
)


def test_recent_worker_is_not_stale() -> None:
    now = datetime.now(UTC)

    assert not is_worker_stale(
        last_heartbeat_at=(
            now - timedelta(seconds=10)
        ),
        now=now,
        stale_after_seconds=60,
    )


def test_old_worker_is_stale() -> None:
    now = datetime.now(UTC)

    assert is_worker_stale(
        last_heartbeat_at=(
            now - timedelta(seconds=120)
        ),
        now=now,
        stale_after_seconds=60,
    )


def test_poll_interval_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="poll_interval_seconds",
    ):
        validate_poll_interval(
            poll_interval_seconds=0
        )


def test_valid_heartbeat_configuration() -> None:
    validate_heartbeat_interval(
        heartbeat_interval_seconds=15,
        stale_after_seconds=60,
    )


def test_heartbeat_must_be_lower_than_stale_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="lower than",
    ):
        validate_heartbeat_interval(
            heartbeat_interval_seconds=60,
            stale_after_seconds=60,
        )