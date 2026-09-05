from __future__ import annotations

from finai.domain.risk.pre_trade import (
    PreTradeRiskDecision,
    PreTradeRiskRequest,
)
from finai.domain.risk.pre_trade_engine import (
    PreTradeRiskEngine,
)


class PreTradeRiskService:
    def __init__(
        self,
        *,
        enabled: bool,
        maximum_order_quantity: float,
        maximum_order_notional: float,
        maximum_position_notional: float,
        maximum_buying_power_fraction: float,
    ) -> None:
        self._engine = PreTradeRiskEngine(
            enabled=enabled,
            maximum_order_quantity=(
                maximum_order_quantity
            ),
            maximum_order_notional=(
                maximum_order_notional
            ),
            maximum_position_notional=(
                maximum_position_notional
            ),
            maximum_buying_power_fraction=(
                maximum_buying_power_fraction
            ),
        )

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        reference_price: float,
        current_position_quantity: float = 0.0,
        buying_power: float | None = None,
    ) -> PreTradeRiskDecision:
        request = PreTradeRiskRequest(
            symbol=symbol,
            side=side,
            quantity=quantity,
            reference_price=reference_price,
            current_position_quantity=(
                current_position_quantity
            ),
            buying_power=buying_power,
        )

        return self._engine.evaluate(
            request=request
        )

    def require_approval(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        reference_price: float,
        current_position_quantity: float = 0.0,
        buying_power: float | None = None,
    ) -> PreTradeRiskDecision:
        decision = self.evaluate(
            symbol=symbol,
            side=side,
            quantity=quantity,
            reference_price=reference_price,
            current_position_quantity=(
                current_position_quantity
            ),
            buying_power=buying_power,
        )

        if not decision.approved:
            raise ValueError(
                "Pre-trade risk rejected order: "
                f"{decision.reason}"
            )

        return decision