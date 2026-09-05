import pytest

from finai.domain.risk.pre_trade import (
    PreTradeRiskRequest,
)
from finai.domain.risk.pre_trade_engine import (
    PreTradeRiskEngine,
)


def make_engine(
    *,
    enabled: bool = True,
) -> PreTradeRiskEngine:
    return PreTradeRiskEngine(
        enabled=enabled,
        maximum_order_quantity=100.0,
        maximum_order_notional=25_000.0,
        maximum_position_notional=50_000.0,
        maximum_buying_power_fraction=0.10,
    )


def test_approves_small_buy() -> None:
    decision = make_engine().evaluate(
        request=PreTradeRiskRequest(
            symbol="AAPL",
            side="buy",
            quantity=1.0,
            reference_price=250.0,
            buying_power=100_000.0,
        )
    )

    assert decision.approved is True
    assert decision.reason is None
    assert decision.order_notional == 250.0
    assert decision.projected_position_quantity == 1.0


def test_rejects_excessive_quantity() -> None:
    decision = make_engine().evaluate(
        request=PreTradeRiskRequest(
            symbol="AAPL",
            side="buy",
            quantity=101.0,
            reference_price=100.0,
            buying_power=1_000_000.0,
        )
    )

    assert decision.approved is False

    assert decision.reason is not None

    assert "quantity" in decision.reason.lower()


def test_rejects_excessive_order_notional() -> None:
    decision = make_engine().evaluate(
        request=PreTradeRiskRequest(
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            reference_price=300.0,
            buying_power=1_000_000.0,
        )
    )

    assert decision.approved is False

    assert decision.reason is not None

    assert "notional" in decision.reason.lower()


def test_rejects_projected_position_notional() -> None:
    decision = make_engine().evaluate(
        request=PreTradeRiskRequest(
            symbol="AAPL",
            side="buy",
            quantity=40.0,
            reference_price=500.0,
            current_position_quantity=70.0,
            buying_power=1_000_000.0,
        )
    )

    assert decision.approved is False

    assert decision.reason is not None

    assert "position" in decision.reason.lower()

    assert decision.order_notional == 20_000.0

    assert (
        decision.projected_position_quantity
        == 110.0
    )

    assert (
        decision.projected_position_notional
        == 55_000.0
    )

    assert decision.approved is False

    assert decision.reason is not None

    assert "position" in decision.reason.lower()


def test_rejects_buying_power_fraction() -> None:
    decision = make_engine().evaluate(
        request=PreTradeRiskRequest(
            symbol="AAPL",
            side="buy",
            quantity=10.0,
            reference_price=500.0,
            buying_power=20_000.0,
        )
    )

    assert decision.approved is False

    assert decision.reason is not None

    assert "buying-power" in decision.reason.lower()


def test_sell_reduces_existing_long_position() -> None:
    decision = make_engine().evaluate(
        request=PreTradeRiskRequest(
            symbol="AAPL",
            side="sell",
            quantity=5.0,
            reference_price=250.0,
            current_position_quantity=10.0,
        )
    )

    assert decision.approved is True

    assert (
        decision.projected_position_quantity
        == 5.0
    )


def test_disabled_engine_allows_order() -> None:
    decision = make_engine(
        enabled=False
    ).evaluate(
        request=PreTradeRiskRequest(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            reference_price=1000.0,
        )
    )

    assert decision.approved is True


@pytest.mark.parametrize(
    (
        "quantity",
        "reference_price",
    ),
    [
        (0.0, 100.0),
        (-1.0, 100.0),
        (1.0, 0.0),
        (1.0, -100.0),
    ],
)
def test_invalid_numeric_inputs_are_rejected(
    quantity: float,
    reference_price: float,
) -> None:
    with pytest.raises(
        ValueError
    ):
        make_engine().evaluate(
            request=PreTradeRiskRequest(
                symbol="AAPL",
                side="buy",
                quantity=quantity,
                reference_price=reference_price,
            )
        )