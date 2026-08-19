from datetime import datetime, timedelta


def calculate_retry_delay_seconds(
    *,
    failure_count: int,
    base_delay_seconds: int,
    maximum_delay_seconds: int,
) -> int:
    if failure_count <= 0:
        raise ValueError(
            "failure_count must be greater than zero."
        )

    if base_delay_seconds <= 0:
        raise ValueError(
            "base_delay_seconds must be greater than zero."
        )

    if maximum_delay_seconds <= 0:
        raise ValueError(
            "maximum_delay_seconds must be greater than zero."
        )

    if maximum_delay_seconds < base_delay_seconds:
        raise ValueError(
            "maximum_delay_seconds cannot be lower "
            "than base_delay_seconds."
        )

    multiplier = 2 ** (failure_count - 1)

    delay = base_delay_seconds * multiplier

    return min(
        delay,
        maximum_delay_seconds,
    )


def calculate_retry_at(
    *,
    now: datetime,
    failure_count: int,
    base_delay_seconds: int,
    maximum_delay_seconds: int,
) -> datetime:
    delay_seconds = calculate_retry_delay_seconds(
        failure_count=failure_count,
        base_delay_seconds=base_delay_seconds,
        maximum_delay_seconds=maximum_delay_seconds,
    )

    return now + timedelta(
        seconds=delay_seconds
    )