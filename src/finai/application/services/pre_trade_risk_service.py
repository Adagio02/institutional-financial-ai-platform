from finai.domain.execution.entities import (
    OrderRiskDecision,
)
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
)


class PreTradeRiskService:
    def evaluate(
        self,
        *,
        order_notional: float,
        current_position_notional: float,
        current_gross_exposure: float,
        account_equity: float,
        account_cash: float,
        is_buy: bool,
        limits: PortfolioRiskLimits,
    ) -> OrderRiskDecision:
        requested_notional = abs(order_notional)

        if requested_notional > (limits.maximum_order_notional):
            return OrderRiskDecision(
                approved=False,
                reason=("Order exceeds maximum order notional."),
                requested_notional=(requested_notional),
                projected_gross_exposure=(current_gross_exposure),
            )

        projected_position = abs(current_position_notional + order_notional)

        if projected_position > (limits.maximum_position_notional):
            return OrderRiskDecision(
                approved=False,
                reason=("Order exceeds maximum position notional."),
                requested_notional=(requested_notional),
                projected_gross_exposure=(current_gross_exposure),
            )

        if account_equity <= 0:
            return OrderRiskDecision(
                approved=False,
                reason=("Account equity is not positive."),
                requested_notional=(requested_notional),
                projected_gross_exposure=(current_gross_exposure),
            )

        position_fraction = projected_position / account_equity

        if position_fraction > (limits.maximum_position_fraction):
            return OrderRiskDecision(
                approved=False,
                reason=("Order exceeds maximum portfolio position fraction."),
                requested_notional=(requested_notional),
                projected_gross_exposure=(current_gross_exposure),
            )

        projected_gross_exposure = current_gross_exposure + requested_notional

        if projected_gross_exposure > (limits.maximum_gross_exposure):
            return OrderRiskDecision(
                approved=False,
                reason=("Order exceeds maximum gross exposure."),
                requested_notional=(requested_notional),
                projected_gross_exposure=(projected_gross_exposure),
            )

        if is_buy:
            projected_cash = account_cash - requested_notional

            minimum_cash = account_equity * limits.minimum_cash_reserve_fraction

            if projected_cash < minimum_cash:
                return OrderRiskDecision(
                    approved=False,
                    reason=("Order violates minimum cash reserve."),
                    requested_notional=(requested_notional),
                    projected_gross_exposure=(projected_gross_exposure),
                )

        return OrderRiskDecision(
            approved=True,
            reason=None,
            requested_notional=(requested_notional),
            projected_gross_exposure=(projected_gross_exposure),
        )
