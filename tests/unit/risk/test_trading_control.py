from finai.domain.risk.trading_control import (
    TradingControlReason,
    evaluate_trading_controls,
)


def test_normal_order_is_approved() -> None:
    result = evaluate_trading_controls(
        trading_enabled=True,
        manual_halt=False,
        circuit_breaker_tripped=False,
        account_equity=100_000,
        day_start_equity=100_000,
        current_gross_exposure=20_000,
        current_symbol_exposure=5_000,
        proposed_order_notional=5_000,
        maximum_daily_loss_fraction=0.05,
        maximum_gross_exposure_fraction=1.50,
        maximum_symbol_fraction=0.25,
        maximum_order_fraction=0.10,
    )

    assert result.approved
    assert result.reason is None


def test_manual_halt_rejects_order() -> None:
    result = evaluate_trading_controls(
        trading_enabled=True,
        manual_halt=True,
        circuit_breaker_tripped=False,
        account_equity=100_000,
        day_start_equity=100_000,
        current_gross_exposure=0,
        current_symbol_exposure=0,
        proposed_order_notional=1_000,
        maximum_daily_loss_fraction=0.05,
        maximum_gross_exposure_fraction=1.50,
        maximum_symbol_fraction=0.25,
        maximum_order_fraction=0.10,
    )

    assert not result.approved

    assert (
        result.reason
        == TradingControlReason.MANUAL_HALT
    )


def test_daily_loss_trips_control() -> None:
    result = evaluate_trading_controls(
        trading_enabled=True,
        manual_halt=False,
        circuit_breaker_tripped=False,
        account_equity=94_000,
        day_start_equity=100_000,
        current_gross_exposure=20_000,
        current_symbol_exposure=5_000,
        proposed_order_notional=1_000,
        maximum_daily_loss_fraction=0.05,
        maximum_gross_exposure_fraction=1.50,
        maximum_symbol_fraction=0.25,
        maximum_order_fraction=0.10,
    )

    assert not result.approved

    assert (
        result.reason
        == TradingControlReason.DAILY_LOSS_LIMIT
    )


def test_symbol_concentration_is_rejected() -> None:
    result = evaluate_trading_controls(
        trading_enabled=True,
        manual_halt=False,
        circuit_breaker_tripped=False,
        account_equity=100_000,
        day_start_equity=100_000,
        current_gross_exposure=30_000,
        current_symbol_exposure=24_000,
        proposed_order_notional=2_000,
        maximum_daily_loss_fraction=0.05,
        maximum_gross_exposure_fraction=1.50,
        maximum_symbol_fraction=0.25,
        maximum_order_fraction=0.10,
    )

    assert not result.approved

    assert (
        result.reason
        == (
            TradingControlReason
            .SYMBOL_CONCENTRATION_LIMIT
        )
    )


def test_large_order_is_rejected() -> None:
    result = evaluate_trading_controls(
        trading_enabled=True,
        manual_halt=False,
        circuit_breaker_tripped=False,
        account_equity=100_000,
        day_start_equity=100_000,
        current_gross_exposure=0,
        current_symbol_exposure=0,
        proposed_order_notional=11_000,
        maximum_daily_loss_fraction=0.05,
        maximum_gross_exposure_fraction=1.50,
        maximum_symbol_fraction=0.25,
        maximum_order_fraction=0.10,
    )

    assert not result.approved

    assert (
        result.reason
        == TradingControlReason.ORDER_NOTIONAL_LIMIT
    )