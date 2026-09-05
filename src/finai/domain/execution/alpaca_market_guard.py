from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaMarketGuardResult:
    symbol: str

    asset_status: str

    tradable: bool

    fractionable: bool

    market_open: bool

    clock_timestamp: str | None

    next_open: str | None

    next_close: str | None


class AlpacaMarketGuard:
    def __init__(
        self,
        *,
        require_active_asset: bool,
        require_tradable_asset: bool,
        require_market_open: bool,
        require_fractionable: bool,
    ) -> None:
        self._require_active_asset = (
            require_active_asset
        )

        self._require_tradable_asset = (
            require_tradable_asset
        )

        self._require_market_open = (
            require_market_open
        )

        self._require_fractionable = (
            require_fractionable
        )

    def validate_order(
        self,
        *,
        asset: dict[str, Any],
        clock: dict[str, Any],
        symbol: str,
        quantity: float,
    ) -> AlpacaMarketGuardResult:
        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        if not normalized_symbol:
            raise ValueError(
                "symbol cannot be blank."
            )

        if quantity <= 0:
            raise ValueError(
                "Order quantity must "
                "be positive."
            )

        asset_symbol = str(
            asset.get(
                "symbol",
                "",
            )
        ).strip().upper()

        if not asset_symbol:
            raise ValueError(
                "Alpaca asset response "
                "contains no symbol."
            )

        if (
            asset_symbol
            != normalized_symbol
        ):
            raise ValueError(
                "Alpaca asset symbol "
                "does not match the "
                "requested symbol."
            )

        asset_status = str(
            asset.get(
                "status",
                "",
            )
        ).strip().lower()

        tradable = self._as_bool(
            asset.get(
                "tradable",
                False,
            )
        )

        fractionable = self._as_bool(
            asset.get(
                "fractionable",
                False,
            )
        )

        market_open = self._as_bool(
            clock.get(
                "is_open",
                False,
            )
        )

        if (
            self._require_active_asset
            and asset_status != "active"
        ):
            raise ValueError(
                "Alpaca asset is not "
                "active. "
                f"symbol={normalized_symbol}, "
                f"status="
                f"{asset_status or 'unknown'}."
            )

        if (
            self._require_tradable_asset
            and not tradable
        ):
            raise ValueError(
                "Alpaca asset is not "
                "tradable. "
                f"symbol="
                f"{normalized_symbol}."
            )

        fractional_quantity = (
            not self._is_whole_number(
                quantity
            )
        )

        if (
            self._require_fractionable
            and fractional_quantity
            and not fractionable
        ):
            raise ValueError(
                "Fractional quantity was "
                "requested for a "
                "non-fractionable Alpaca "
                "asset."
            )

        if (
            self._require_market_open
            and not market_open
        ):
            raise ValueError(
                "Alpaca market is closed. "
                "Order submission is "
                "blocked by the V2.6 "
                "market-session guard."
            )

        return AlpacaMarketGuardResult(
            symbol=normalized_symbol,
            asset_status=(
                asset_status
            ),
            tradable=tradable,
            fractionable=(
                fractionable
            ),
            market_open=(
                market_open
            ),
            clock_timestamp=(
                self._optional_string(
                    clock.get(
                        "timestamp"
                    )
                )
            ),
            next_open=(
                self._optional_string(
                    clock.get(
                        "next_open"
                    )
                )
            ),
            next_close=(
                self._optional_string(
                    clock.get(
                        "next_close"
                    )
                )
            ),
        )

    @staticmethod
    def _is_whole_number(
        quantity: float,
    ) -> bool:
        return abs(
            quantity
            - round(
                quantity
            )
        ) <= 1e-9

    @staticmethod
    def _optional_string(
        value: Any,
    ) -> str | None:
        if value in {
            None,
            "",
        }:
            return None

        return str(
            value
        )

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