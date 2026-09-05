from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PortfolioRiskLimits:
    maximum_order_notional: float
    maximum_position_notional: float
    maximum_gross_exposure: float
    maximum_position_fraction: float
    minimum_cash_reserve_fraction: float


def validate_risk_limits(
    limits: PortfolioRiskLimits,
) -> None:
    if limits.maximum_order_notional <= 0:
        raise ValueError("maximum_order_notional must be positive.")

    if limits.maximum_position_notional <= 0:
        raise ValueError("maximum_position_notional must be positive.")

    if limits.maximum_gross_exposure <= 0:
        raise ValueError("maximum_gross_exposure must be positive.")

    if not 0 < limits.maximum_position_fraction <= 1:
        raise ValueError("maximum_position_fraction must be between zero and one.")

    if not 0 <= limits.minimum_cash_reserve_fraction < 1:
        raise ValueError("minimum_cash_reserve_fraction must be between zero and one.")
