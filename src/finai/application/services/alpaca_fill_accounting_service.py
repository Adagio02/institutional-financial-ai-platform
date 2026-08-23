from sqlalchemy.orm import Session

from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.execution.position_accounting import (
    apply_fill_to_position,
)
from finai.infrastructure.database.repositories.execution_fill_repository import (
    ExecutionFillRepository,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)


class AlpacaFillAccountingService:
    def __init__(
        self,
        *,
        session: Session,
        commission_bps: float,
    ) -> None:
        self._account_repository = (
            PaperAccountRepository(
                session
            )
        )

        self._position_repository = (
            PaperPositionRepository(
                session
            )
        )

        self._fill_repository = (
            ExecutionFillRepository(
                session
            )
        )

        self._commission_bps = (
            commission_bps
        )

    def apply_cumulative_fill(
        self,
        *,
        order,
        cumulative_filled_quantity: float,
        cumulative_average_price: float | None,
    ) -> float:
        previous_quantity = float(
            order.filled_quantity or 0.0
        )

        new_quantity = float(
            cumulative_filled_quantity
        )

        delta_quantity = (
            new_quantity
            - previous_quantity
        )

        if delta_quantity <= 0:
            return 0.0

        if cumulative_average_price is None:
            raise ValueError(
                "Filled Alpaca order has no "
                "average fill price."
            )

        new_average = float(
            cumulative_average_price
        )

        previous_average = float(
            order.average_fill_price or 0.0
        )

        cumulative_notional = (
            new_quantity
            * new_average
        )

        previous_notional = (
            previous_quantity
            * previous_average
        )

        delta_notional = (
            cumulative_notional
            - previous_notional
        )

        if delta_notional <= 0:
            delta_price = new_average
            delta_notional = (
                delta_quantity
                * delta_price
            )
        else:
            delta_price = (
                delta_notional
                / delta_quantity
            )

        commission = (
            delta_notional
            * self._commission_bps
            / 10_000.0
        )

        self._fill_repository.create(
            order_id=order.id,
            quantity=delta_quantity,
            price=delta_price,
            notional=delta_notional,
            commission=commission,
            slippage_cost=0.0,
        )

        account = (
            self._account_repository
            .get_by_id(
                order.account_id
            )
        )

        if account is None:
            raise LookupError(
                "Paper account was not found."
            )

        position = (
            self._position_repository
            .get(
                account_id=account.id,
                instrument_id=(
                    order.instrument_id
                ),
            )
        )

        if position is None:
            position = (
                self._position_repository
                .create(
                    account_id=account.id,
                    instrument_id=(
                        order.instrument_id
                    ),
                    symbol=order.symbol,
                    quantity=0.0,
                    average_price=0.0,
                )
            )

        side = OrderSide(
            order.side
        )

        signed_quantity = (
            delta_quantity
            if side == OrderSide.BUY
            else -delta_quantity
        )

        accounting_result = (
            apply_fill_to_position(
                current_quantity=(
                    position.quantity
                ),
                current_average_price=(
                    position.average_price
                ),
                fill_quantity=(
                    signed_quantity
                ),
                fill_price=delta_price,
            )
        )

        position.quantity = (
            accounting_result.quantity
        )

        position.average_price = (
            accounting_result.average_price
        )

        position.realized_pnl += (
            accounting_result
            .realized_pnl_delta
        )

        self._position_repository.save(
            position
        )

        if side == OrderSide.BUY:
            new_cash = (
                account.cash
                - delta_notional
                - commission
            )

        else:
            new_cash = (
                account.cash
                + delta_notional
                - commission
            )

        new_realized_pnl = (
            account.realized_pnl
            + (
                accounting_result
                .realized_pnl_delta
            )
            - commission
        )

        self._account_repository.update_cash(
            account,
            cash=new_cash,
            realized_pnl=(
                new_realized_pnl
            ),
        )

        return delta_quantity