from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finai.domain.execution.enums import (
    OrderSide,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaAccountGuardResult:
    status: str

    trading_blocked: bool

    account_blocked: bool

    buying_power: float

    cash: float

    equity: float

    estimated_order_notional: float

    maximum_allowed_order_notional: float


class AlpacaAccountGuard:
    def __init__(
        self,
        *,
        require_active: bool,
        maximum_buying_power_fraction: float,
        require_positive_buying_power: bool,
    ) -> None:
        if not (
            0.0
            < maximum_buying_power_fraction
            <= 1.0
        ):
            raise ValueError(
                "maximum_buying_power_fraction "
                "must be greater than 0 and "
                "less than or equal to 1."
            )

        self._require_active = (
            require_active
        )

        self._maximum_buying_power_fraction = (
            maximum_buying_power_fraction
        )

        self._require_positive_buying_power = (
            require_positive_buying_power
        )

    def validate_order(
        self,
        *,
        account: dict[str, Any],
        side: OrderSide,
        quantity: float,
        reference_price: float,
    ) -> AlpacaAccountGuardResult:
        if quantity <= 0:
            raise ValueError(
                "Order quantity must be positive."
            )

        if reference_price <= 0:
            raise ValueError(
                "Reference price must be positive."
            )

        status = str(
            account.get(
                "status",
                "",
            )
        ).strip().upper()

        trading_blocked = self._as_bool(
            account.get(
                "trading_blocked",
                False,
            )
        )

        account_blocked = self._as_bool(
            account.get(
                "account_blocked",
                False,
            )
        )

        buying_power = self._required_float(
            account=account,
            field_name="buying_power",
        )

        cash = self._required_float(
            account=account,
            field_name="cash",
        )

        equity = self._required_float(
            account=account,
            field_name="equity",
        )

        if (
            self._require_active
            and status != "ACTIVE"
        ):
            raise ValueError(
                "Alpaca account is not ACTIVE. "
                f"Current status: "
                f"{status or 'UNKNOWN'}."
            )

        if trading_blocked:
            raise ValueError(
                "Alpaca has blocked trading "
                "for this account."
            )

        if account_blocked:
            raise ValueError(
                "Alpaca account is blocked."
            )

        if equity < 0:
            raise ValueError(
                "Alpaca account equity "
                "cannot be negative."
            )

        if (
            self._require_positive_buying_power
            and buying_power <= 0
        ):
            raise ValueError(
                "Alpaca account has no "
                "positive buying power."
            )

        estimated_order_notional = (
            float(quantity)
            * float(reference_price)
        )

        maximum_allowed_order_notional = (
            buying_power
            * self._maximum_buying_power_fraction
        )

        if (
            side == OrderSide.BUY
            and estimated_order_notional
            > maximum_allowed_order_notional
        ):
            raise ValueError(
                "Order exceeds the configured "
                "Alpaca buying-power guard. "
                f"estimated_notional="
                f"{estimated_order_notional:.2f}, "
                f"maximum_allowed="
                f"{maximum_allowed_order_notional:.2f}."
            )

        return AlpacaAccountGuardResult(
            status=status,
            trading_blocked=(
                trading_blocked
            ),
            account_blocked=(
                account_blocked
            ),
            buying_power=(
                buying_power
            ),
            cash=cash,
            equity=equity,
            estimated_order_notional=(
                estimated_order_notional
            ),
            maximum_allowed_order_notional=(
                maximum_allowed_order_notional
            ),
        )

    @staticmethod
    def _required_float(
        *,
        account: dict[str, Any],
        field_name: str,
    ) -> float:
        if field_name not in account:
            raise ValueError(
                f"Alpaca account field "
                f"{field_name} is missing."
            )

        value = account[
            field_name
        ]

        if value in {
            None,
            "",
        }:
            raise ValueError(
                f"Alpaca account field "
                f"{field_name} is missing."
            )

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                f"Alpaca account field "
                f"{field_name} is invalid."
            ) from error

    @staticmethod
    def _as_bool(
        value: Any,
    ) -> bool:
        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            normalized = (
                value
                .strip()
                .lower()
            )

            if normalized in {
                "true",
                "1",
                "yes",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "",
            }:
                return False

        return bool(
            value
        )