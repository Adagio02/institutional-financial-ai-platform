import pytest

from finai.domain.execution.alpaca_account_guard import (
    AlpacaAccountGuard,
)
from finai.domain.execution.enums import (
    OrderSide,
)


def make_guard() -> AlpacaAccountGuard:
    return AlpacaAccountGuard(
        require_active=True,
        maximum_buying_power_fraction=0.10,
        require_positive_buying_power=True,
    )


def make_account(
    *,
    status: str = "ACTIVE",
    trading_blocked: bool = False,
    account_blocked: bool = False,
    buying_power: str = "100000",
    cash: str = "50000",
    equity: str = "100000",
) -> dict:
    return {
        "status": status,
        "trading_blocked": (
            trading_blocked
        ),
        "account_blocked": (
            account_blocked
        ),
        "buying_power": (
            buying_power
        ),
        "cash": cash,
        "equity": equity,
    }


def test_valid_buy_passes() -> None:
    result = (
        make_guard()
        .validate_order(
            account=(
                make_account()
            ),
            side=(
                OrderSide.BUY
            ),
            quantity=1.0,
            reference_price=250.0,
        )
    )

    assert result.status == "ACTIVE"

    assert (
        result
        .estimated_order_notional
        == 250.0
    )

    assert (
        result
        .maximum_allowed_order_notional
        == 10000.0
    )


def test_non_active_account_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="not ACTIVE",
    ):
        (
            make_guard()
            .validate_order(
                account=(
                    make_account(
                        status="DISABLED"
                    )
                ),
                side=(
                    OrderSide.BUY
                ),
                quantity=1.0,
                reference_price=250.0,
            )
        )


def test_trading_blocked_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="blocked trading",
    ):
        (
            make_guard()
            .validate_order(
                account=(
                    make_account(
                        trading_blocked=True
                    )
                ),
                side=(
                    OrderSide.BUY
                ),
                quantity=1.0,
                reference_price=250.0,
            )
        )


def test_account_blocked_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="account is blocked",
    ):
        (
            make_guard()
            .validate_order(
                account=(
                    make_account(
                        account_blocked=True
                    )
                ),
                side=(
                    OrderSide.BUY
                ),
                quantity=1.0,
                reference_price=250.0,
            )
        )


def test_zero_buying_power_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="positive buying power",
    ):
        (
            make_guard()
            .validate_order(
                account=(
                    make_account(
                        buying_power="0"
                    )
                ),
                side=(
                    OrderSide.BUY
                ),
                quantity=1.0,
                reference_price=250.0,
            )
        )


def test_buy_over_fraction_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="buying-power guard",
    ):
        (
            make_guard()
            .validate_order(
                account=(
                    make_account(
                        buying_power="10000"
                    )
                ),
                side=(
                    OrderSide.BUY
                ),
                quantity=10.0,
                reference_price=250.0,
            )
        )


def test_sell_does_not_use_buy_fraction() -> None:
    result = (
        make_guard()
        .validate_order(
            account=(
                make_account(
                    buying_power="1000"
                )
            ),
            side=(
                OrderSide.SELL
            ),
            quantity=100.0,
            reference_price=250.0,
        )
    )

    assert (
        result
        .estimated_order_notional
        == 25000.0
    )


def test_missing_buying_power_is_rejected() -> None:
    account = make_account()

    account.pop(
        "buying_power"
    )

    with pytest.raises(
        ValueError,
        match="buying_power",
    ):
        (
            make_guard()
            .validate_order(
                account=account,
                side=(
                    OrderSide.BUY
                ),
                quantity=1.0,
                reference_price=250.0,
            )
        )


def test_invalid_fraction_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "maximum_buying_power_fraction"
        ),
    ):
        AlpacaAccountGuard(
            require_active=True,
            maximum_buying_power_fraction=1.5,
            require_positive_buying_power=True,
        )