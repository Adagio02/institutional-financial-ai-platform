from __future__ import annotations

from finai.domain.risk.pre_trade import (
    PreTradeRiskDecision,
    PreTradeRiskRequest,
)


class PreTradeRiskEngine:
    def __init__(
        self,
        *,
        enabled: bool,
        maximum_order_quantity: float,
        maximum_order_notional: float,
        maximum_position_notional: float,
        maximum_buying_power_fraction: float,
    ) -> None:
        if maximum_order_quantity <= 0:
            raise ValueError(
                "maximum_order_quantity must be positive."
            )

        if maximum_order_notional <= 0:
            raise ValueError(
                "maximum_order_notional must be positive."
            )

        if maximum_position_notional <= 0:
            raise ValueError(
                "maximum_position_notional must be positive."
            )

        if not (
            0
            < maximum_buying_power_fraction
            <= 1
        ):
            raise ValueError(
                "maximum_buying_power_fraction must be "
                "greater than 0 and less than or equal to 1."
            )

        self._enabled = enabled

        self._maximum_order_quantity = (
            maximum_order_quantity
        )

        self._maximum_order_notional = (
            maximum_order_notional
        )

        self._maximum_position_notional = (
            maximum_position_notional
        )

        self._maximum_buying_power_fraction = (
            maximum_buying_power_fraction
        )

    def evaluate(
        self,
        *,
        request: PreTradeRiskRequest,
    ) -> PreTradeRiskDecision:
        symbol = (
            request.symbol
            .strip()
            .upper()
        )

        side = (
            request.side
            .strip()
            .lower()
        )

        if not symbol:
            raise ValueError(
                "symbol cannot be empty."
            )

        if side not in {
            "buy",
            "sell",
        }:
            raise ValueError(
                "side must be buy or sell."
            )

        if request.quantity <= 0:
            raise ValueError(
                "quantity must be positive."
            )

        if request.reference_price <= 0:
            raise ValueError(
                "reference_price must be positive."
            )

        order_notional = (
            request.quantity
            * request.reference_price
        )

        signed_quantity = (
            request.quantity
            if side == "buy"
            else -request.quantity
        )

        projected_position_quantity = (
            request.current_position_quantity
            + signed_quantity
        )

        projected_position_notional = (
            abs(
                projected_position_quantity
            )
            * request.reference_price
        )

        if not self._enabled:
            return self._decision(
                approved=True,
                reason=None,
                request=request,
                symbol=symbol,
                side=side,
                order_notional=order_notional,
                projected_position_quantity=(
                    projected_position_quantity
                ),
                projected_position_notional=(
                    projected_position_notional
                ),
            )

        if (
            request.quantity
            > self._maximum_order_quantity
        ):
            return self._decision(
                approved=False,
                reason=(
                    "Order quantity exceeds the "
                    "configured maximum."
                ),
                request=request,
                symbol=symbol,
                side=side,
                order_notional=order_notional,
                projected_position_quantity=(
                    projected_position_quantity
                ),
                projected_position_notional=(
                    projected_position_notional
                ),
            )

        if (
            order_notional
            > self._maximum_order_notional
        ):
            return self._decision(
                approved=False,
                reason=(
                    "Order notional exceeds the "
                    "configured maximum."
                ),
                request=request,
                symbol=symbol,
                side=side,
                order_notional=order_notional,
                projected_position_quantity=(
                    projected_position_quantity
                ),
                projected_position_notional=(
                    projected_position_notional
                ),
            )

        if (
            projected_position_notional
            > self._maximum_position_notional
        ):
            return self._decision(
                approved=False,
                reason=(
                    "Projected position notional exceeds "
                    "the configured maximum."
                ),
                request=request,
                symbol=symbol,
                side=side,
                order_notional=order_notional,
                projected_position_quantity=(
                    projected_position_quantity
                ),
                projected_position_notional=(
                    projected_position_notional
                ),
            )

        if (
            side == "buy"
            and request.buying_power is not None
        ):
            if request.buying_power <= 0:
                return self._decision(
                    approved=False,
                    reason=(
                        "Buying power must be positive "
                        "for buy orders."
                    ),
                    request=request,
                    symbol=symbol,
                    side=side,
                    order_notional=order_notional,
                    projected_position_quantity=(
                        projected_position_quantity
                    ),
                    projected_position_notional=(
                        projected_position_notional
                    ),
                )

            maximum_buying_power_notional = (
                request.buying_power
                * self._maximum_buying_power_fraction
            )

            if (
                order_notional
                > maximum_buying_power_notional
            ):
                return self._decision(
                    approved=False,
                    reason=(
                        "Order notional exceeds the "
                        "configured buying-power fraction."
                    ),
                    request=request,
                    symbol=symbol,
                    side=side,
                    order_notional=order_notional,
                    projected_position_quantity=(
                        projected_position_quantity
                    ),
                    projected_position_notional=(
                        projected_position_notional
                    ),
                )

        return self._decision(
            approved=True,
            reason=None,
            request=request,
            symbol=symbol,
            side=side,
            order_notional=order_notional,
            projected_position_quantity=(
                projected_position_quantity
            ),
            projected_position_notional=(
                projected_position_notional
            ),
        )

    @staticmethod
    def _decision(
        *,
        approved: bool,
        reason: str | None,
        request: PreTradeRiskRequest,
        symbol: str,
        side: str,
        order_notional: float,
        projected_position_quantity: float,
        projected_position_notional: float,
    ) -> PreTradeRiskDecision:
        return PreTradeRiskDecision(
            approved=approved,
            reason=reason,
            symbol=symbol,
            side=side,
            quantity=request.quantity,
            reference_price=request.reference_price,
            order_notional=order_notional,
            projected_position_quantity=(
                projected_position_quantity
            ),
            projected_position_notional=(
                projected_position_notional
            ),
        )