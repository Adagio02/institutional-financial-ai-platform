from datetime import datetime, timedelta


def is_worker_stale(
    *,
    last_heartbeat_at: datetime,
    now: datetime,
    stale_after_seconds: int,
) -> bool:
    if stale_after_seconds <= 0:
        raise ValueError(
            "stale_after_seconds must be greater than zero."
        )

    return (
        last_heartbeat_at
        + timedelta(seconds=stale_after_seconds)
        < now
    )


def validate_poll_interval(
    *,
    poll_interval_seconds: int,
) -> None:
    if poll_interval_seconds <= 0:
        raise ValueError(
            "poll_interval_seconds must be greater than zero."
        )


def validate_heartbeat_interval(
    *,
    heartbeat_interval_seconds: int,
    stale_after_seconds: int,
) -> None:
    if heartbeat_interval_seconds <= 0:
        raise ValueError(
            "heartbeat_interval_seconds must be greater than zero."
        )

    if stale_after_seconds <= 0:
        raise ValueError(
            "stale_after_seconds must be greater than zero."
        )

    if heartbeat_interval_seconds >= stale_after_seconds:
        raise ValueError(
            "heartbeat_interval_seconds must be lower "
            "than stale_after_seconds."
        )