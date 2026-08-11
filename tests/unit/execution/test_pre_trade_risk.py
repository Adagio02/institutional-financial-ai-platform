from finai.application.services.pre_trade_risk_service import (
    PreTradeRiskService,
)
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
)


def create_limits() -> PortfolioRiskLimits:
    return PortfolioRiskLimits(
        maximum_order_notional=25_000.0,
        maximum_position_notional=50_000.0,
        maximum_gross_exposure=100_000.0,
        maximum_position_fraction=0.50,
        minimum_cash_reserve_fraction=0.05,
    )


def test_valid_order_is_approved() -> None:
    service = PreTradeRiskService()

    result = service.evaluate(
        order_notional=10_000.0,
        current_position_notional=0.0,
        current_gross_exposure=0.0,
        account_equity=100_000.0,
        account_cash=100_000.0,
        is_buy=True,
        limits=create_limits(),
    )

    assert result.approved is True


def test_large_order_is_rejected() -> None:
    service = PreTradeRiskService()

    result = service.evaluate(
        order_notional=30_000.0,
        current_position_notional=0.0,
        current_gross_exposure=0.0,
        account_equity=100_000.0,
        account_cash=100_000.0,
        is_buy=True,
        limits=create_limits(),
    )

    assert result.approved is False
    assert "order notional" in (result.reason or "").lower()


def test_cash_reserve_is_enforced() -> None:
    service = PreTradeRiskService()

    result = service.evaluate(
        order_notional=20_000.0,
        current_position_notional=0.0,
        current_gross_exposure=0.0,
        account_equity=100_000.0,
        account_cash=22_000.0,
        is_buy=True,
        limits=create_limits(),
    )

    assert result.approved is False
    assert "cash reserve" in (result.reason or "").lower()
