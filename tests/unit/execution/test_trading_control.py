import pytest

from finai.domain.execution.control import (
    TradingControlState,
    validate_trading_control,
)


def test_enabled_control_can_trade() -> None:
    state = TradingControlState(
        trading_enabled=True,
        kill_switch_active=False,
        reason=None,
    )

    assert state.can_trade is True


def test_disabled_control_cannot_trade() -> None:
    state = TradingControlState(
        trading_enabled=False,
        kill_switch_active=False,
        reason="Maintenance",
    )

    assert state.can_trade is False


def test_kill_switch_blocks_trading() -> None:
    state = TradingControlState(
        trading_enabled=False,
        kill_switch_active=True,
        reason="Risk event",
    )

    assert state.can_trade is False


def test_kill_switch_requires_reason() -> None:
    with pytest.raises(
        ValueError,
        match="reason",
    ):
        validate_trading_control(
            trading_enabled=False,
            kill_switch_active=True,
            reason=None,
        )


def test_cannot_enable_with_kill_switch() -> None:
    with pytest.raises(
        ValueError,
        match="kill switch",
    ):
        validate_trading_control(
            trading_enabled=True,
            kill_switch_active=True,
            reason="Emergency",
        )
