from finai.application.services.pre_trade_risk_service import (
    PreTradeRiskService,
)


def make_service() -> PreTradeRiskService:
    return PreTradeRiskService(
        enabled=True,
        maximum_order_quantity=100.0,
        maximum_order_notional=25_000.0,
        maximum_position_notional=50_000.0,
        maximum_buying_power_fraction=0.10,
    )


def test_valid_order_is_approved() -> None:
    service = make_service()

    result = service.evaluate(
        symbol="AAPL",
        side="buy",
        quantity=10.0,
        reference_price=200.0,
        current_position_quantity=0.0,
        buying_power=100_000.0,
    )

    assert result.approved is True
    assert result.reason is None
    assert result.symbol == "AAPL"
    assert result.order_notional == 2_000.0
    assert (
        result.projected_position_quantity
        == 10.0
    )
    assert (
        result.projected_position_notional
        == 2_000.0
    )


def test_large_order_is_rejected() -> None:
    service = make_service()

    result = service.evaluate(
        symbol="AAPL",
        side="buy",
        quantity=60.0,
        reference_price=500.0,
        current_position_quantity=0.0,
        buying_power=1_000_000.0,
    )

    assert result.approved is False
    assert result.reason is not None
    assert "order notional" in result.reason.lower()
    assert result.order_notional == 30_000.0


def test_buying_power_limit_is_enforced() -> None:
    service = make_service()

    result = service.evaluate(
        symbol="AAPL",
        side="buy",
        quantity=10.0,
        reference_price=200.0,
        current_position_quantity=0.0,
        buying_power=10_000.0,
    )

    assert result.approved is False
    assert result.reason is not None
    assert "buying-power" in result.reason.lower()
    assert result.order_notional == 2_000.0