from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pytest

from finai.domain.execution.alpaca_quote_guard import (
    AlpacaQuoteGuard,
)


def make_guard(
) -> AlpacaQuoteGuard:
    return AlpacaQuoteGuard(
        maximum_age_seconds=60,
        maximum_spread_bps=100.0,
        maximum_reference_deviation_bps=250.0,
    )


def make_quote(
    *,
    bid: float = 100.00,
    ask: float = 100.10,
    timestamp: datetime | None = None,
) -> dict:
    resolved_timestamp = (
        timestamp
        or datetime.now(UTC)
    )

    return {
        "bp": bid,
        "ap": ask,
        "bs": 100,
        "as": 100,
        "t": (
            resolved_timestamp
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        ),
    }


def test_valid_quote_passes() -> None:
    now = datetime.now(UTC)

    result = (
        make_guard()
        .validate_quote(
            symbol="AAPL",
            quote=make_quote(
                timestamp=now
            ),
            reference_price=100.05,
            now=now,
        )
    )

    assert (
        result.symbol
        == "AAPL"
    )

    assert result.midpoint == pytest.approx(
        100.05
    )

    assert (
        result.quote_age_seconds
        == pytest.approx(
            0.0
        )
    )


def test_stale_quote_is_rejected() -> None:
    now = datetime.now(UTC)

    stale = (
        now
        - timedelta(
            seconds=61
        )
    )

    with pytest.raises(
        ValueError,
        match="quote is stale",
    ):
        (
            make_guard()
            .validate_quote(
                symbol="AAPL",
                quote=make_quote(
                    timestamp=stale
                ),
                reference_price=100.05,
                now=now,
            )
        )


def test_wide_spread_is_rejected() -> None:
    now = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="spread",
    ):
        (
            make_guard()
            .validate_quote(
                symbol="AAPL",
                quote=make_quote(
                    bid=100.0,
                    ask=102.0,
                    timestamp=now,
                ),
                reference_price=101.0,
                now=now,
            )
        )


def test_reference_deviation_is_rejected() -> None:
    now = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="reference price",
    ):
        (
            make_guard()
            .validate_quote(
                symbol="AAPL",
                quote=make_quote(
                    timestamp=now
                ),
                reference_price=95.0,
                now=now,
            )
        )


def test_missing_bid_is_rejected() -> None:
    now = datetime.now(UTC)

    quote = make_quote(
        timestamp=now
    )

    quote.pop(
        "bp"
    )

    with pytest.raises(
        ValueError,
        match="bp",
    ):
        (
            make_guard()
            .validate_quote(
                symbol="AAPL",
                quote=quote,
                reference_price=100.05,
                now=now,
            )
        )


def test_ask_below_bid_is_rejected() -> None:
    now = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="ask below bid",
    ):
        (
            make_guard()
            .validate_quote(
                symbol="AAPL",
                quote=make_quote(
                    bid=101.0,
                    ask=100.0,
                    timestamp=now,
                ),
                reference_price=100.5,
                now=now,
            )
        )


def test_future_quote_is_rejected() -> None:
    now = datetime.now(UTC)

    future = (
        now
        + timedelta(
            seconds=10
        )
    )

    with pytest.raises(
        ValueError,
        match="future",
    ):
        (
            make_guard()
            .validate_quote(
                symbol="AAPL",
                quote=make_quote(
                    timestamp=future
                ),
                reference_price=100.05,
                now=now,
            )
        )