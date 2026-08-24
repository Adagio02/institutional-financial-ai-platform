import pytest

from finai.domain.execution.alpaca_market_guard import (
    AlpacaMarketGuard,
)


def make_guard(
    *,
    require_market_open: bool = True,
) -> AlpacaMarketGuard:
    return AlpacaMarketGuard(
        require_active_asset=True,
        require_tradable_asset=True,
        require_market_open=(
            require_market_open
        ),
        require_fractionable=True,
    )


def make_asset(
    *,
    symbol: str = "AAPL",
    status: str = "active",
    tradable: bool = True,
    fractionable: bool = True,
) -> dict:
    return {
        "id": "asset-id",
        "class": "us_equity",
        "exchange": "NASDAQ",
        "symbol": symbol,
        "status": status,
        "tradable": tradable,
        "fractionable": (
            fractionable
        ),
    }


def make_clock(
    *,
    is_open: bool = True,
) -> dict:
    return {
        "timestamp": (
            "2026-08-24T10:30:00-04:00"
        ),
        "is_open": is_open,
        "next_open": (
            "2026-08-25T09:30:00-04:00"
        ),
        "next_close": (
            "2026-08-24T16:00:00-04:00"
        ),
    }


def test_valid_asset_and_open_market_pass() -> None:
    result = (
        make_guard()
        .validate_order(
            asset=make_asset(),
            clock=make_clock(),
            symbol="AAPL",
            quantity=1.0,
        )
    )

    assert (
        result.symbol
        == "AAPL"
    )

    assert (
        result.asset_status
        == "active"
    )

    assert result.tradable is True

    assert (
        result.market_open
        is True
    )


def test_inactive_asset_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="not active",
    ):
        (
            make_guard()
            .validate_order(
                asset=make_asset(
                    status="inactive"
                ),
                clock=make_clock(),
                symbol="AAPL",
                quantity=1.0,
            )
        )


def test_non_tradable_asset_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="not tradable",
    ):
        (
            make_guard()
            .validate_order(
                asset=make_asset(
                    tradable=False
                ),
                clock=make_clock(),
                symbol="AAPL",
                quantity=1.0,
            )
        )


def test_closed_market_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="market is closed",
    ):
        (
            make_guard()
            .validate_order(
                asset=make_asset(),
                clock=make_clock(
                    is_open=False
                ),
                symbol="AAPL",
                quantity=1.0,
            )
        )


def test_whole_quantity_does_not_require_fractionable() -> None:
    result = (
        make_guard()
        .validate_order(
            asset=make_asset(
                fractionable=False
            ),
            clock=make_clock(),
            symbol="AAPL",
            quantity=1.0,
        )
    )

    assert (
        result.fractionable
        is False
    )


def test_fractional_quantity_requires_fractionable_asset() -> None:
    with pytest.raises(
        ValueError,
        match="non-fractionable",
    ):
        (
            make_guard()
            .validate_order(
                asset=make_asset(
                    fractionable=False
                ),
                clock=make_clock(),
                symbol="AAPL",
                quantity=0.5,
            )
        )


def test_fractional_quantity_passes_for_fractionable_asset() -> None:
    result = (
        make_guard()
        .validate_order(
            asset=make_asset(
                fractionable=True
            ),
            clock=make_clock(),
            symbol="AAPL",
            quantity=0.5,
        )
    )

    assert (
        result.fractionable
        is True
    )


def test_symbol_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        (
            make_guard()
            .validate_order(
                asset=make_asset(
                    symbol="MSFT"
                ),
                clock=make_clock(),
                symbol="AAPL",
                quantity=1.0,
            )
        )


def test_market_open_requirement_can_be_disabled() -> None:
    result = (
        make_guard(
            require_market_open=False
        )
        .validate_order(
            asset=make_asset(),
            clock=make_clock(
                is_open=False
            ),
            symbol="AAPL",
            quantity=1.0,
        )
    )

    assert (
        result.market_open
        is False
    )