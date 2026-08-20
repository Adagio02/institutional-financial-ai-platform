from sqlalchemy.orm import Session

from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)
from finai.domain.execution.position_accounting import (
    apply_fill_to_position,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.execution_fill_repository import (
    ExecutionFillRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)
from finai.infrastructure.execution.paper_broker import (
    PaperBroker,
)
from finai.infrastructure.execution.sandbox_broker import (
    SandboxBroker,
)


class PaperExecutionService:
    def __init__(
        self,
        *,
        session: Session,
        commission_bps: float,
        slippage_bps: float,
        partial_fill_enabled: bool = False,
        initial_fill_fraction: float = 1.0,
        execution_mode: str = "paper",
    ) -> None:
        self._account_repository = (
            PaperAccountRepository(
                session
            )
        )

        self._order_repository = (
            OrderRepository(
                session
            )
        )

        self._fill_repository = (
            ExecutionFillRepository(
                session
            )
        )

        self._position_repository = (
            PaperPositionRepository(
                session
            )
        )

        self._audit_repository = (
            ExecutionAuditRepository(
                session
            )
        )

        normalized_execution_mode = (
            execution_mode
            .strip()
            .lower()
        )

        if normalized_execution_mode not in {
            "paper",
            "sandbox",
        }:
            raise ValueError(
                (
                    "execution_mode must be "
                    "'paper' or 'sandbox'."
                )
            )

        self._execution_mode = (
            normalized_execution_mode
        )

        if (
            self._execution_mode
            == "sandbox"
        ):
            self._sandbox_broker = (
                SandboxBroker(
                    commission_bps=(
                        commission_bps
                    ),
                    slippage_bps=(
                        slippage_bps
                    ),
                    partial_fill_enabled=(
                        partial_fill_enabled
                    ),
                    initial_fill_fraction=(
                        initial_fill_fraction
                    ),
                )
            )

            self._paper_broker = None

        else:
            self._paper_broker = (
                PaperBroker(
                    commission_bps=(
                        commission_bps
                    ),
                    slippage_bps=(
                        slippage_bps
                    ),
                )
            )

            self._sandbox_broker = None

    def execute(
        self,
        *,
        order,
        reference_price: float,
    ):
        account = (
            self._account_repository
            .get_by_id(
                order.account_id
            )
        )

        if account is None:
            raise LookupError(
                (
                    "Paper account was "
                    "not found."
                )
            )

        side = OrderSide(
            order.side
        )

        order_type = OrderType(
            order.order_type
        )

        if (
            self._execution_mode
            == "sandbox"
        ):
            return self._execute_sandbox(
                account=account,
                order=order,
                side=side,
                order_type=order_type,
                reference_price=(
                    reference_price
                ),
            )

        return self._execute_paper(
            account=account,
            order=order,
            side=side,
            order_type=order_type,
            reference_price=(
                reference_price
            ),
        )

    def _execute_paper(
        self,
        *,
        account,
        order,
        side: OrderSide,
        order_type: OrderType,
        reference_price: float,
    ):
        if self._paper_broker is None:
            raise RuntimeError(
                (
                    "Paper broker is "
                    "not configured."
                )
            )

        fill = (
            self._paper_broker.execute(
                side=side,
                order_type=order_type,
                quantity=order.quantity,
                reference_price=(
                    reference_price
                ),
                limit_price=(
                    order.limit_price
                ),
            )
        )

        if fill is None:
            self._audit_repository.create(
                account_id=(
                    account.id
                ),
                order_id=(
                    order.id
                ),
                event_type=(
                    "order_not_filled"
                ),
                message=(
                    "Paper order did not "
                    "satisfy execution rules."
                ),
            )

            return None

        self._apply_fill(
            account=account,
            order=order,
            side=side,
            quantity=(
                fill.quantity
            ),
            price=(
                fill.price
            ),
            commission=(
                fill.commission
            ),
            slippage_cost=(
                fill.slippage_cost
            ),
        )

        self._order_repository.update_fill_state(
            order,
            filled_quantity=(
                fill.quantity
            ),
            average_fill_price=(
                fill.price
            ),
            status=(
                OrderStatus.FILLED
            ),
        )

        self._audit_repository.create(
            account_id=(
                account.id
            ),
            order_id=(
                order.id
            ),
            event_type=(
                "order_filled"
            ),
            message=(
                "Paper order was filled."
            ),
            event_data={
                "symbol": (
                    order.symbol
                ),
                "side": (
                    order.side
                ),
                "quantity": (
                    fill.quantity
                ),
                "price": (
                    fill.price
                ),
                "commission": (
                    fill.commission
                ),
            },
        )

        return fill

    def _execute_sandbox(
        self,
        *,
        account,
        order,
        side: OrderSide,
        order_type: OrderType,
        reference_price: float,
    ):
        if self._sandbox_broker is None:
            raise RuntimeError(
                (
                    "Sandbox broker is "
                    "not configured."
                )
            )

        result = (
            self._sandbox_broker.submit(
                order_id=(
                    order.id
                ),
                symbol=(
                    order.symbol
                ),
                side=side,
                order_type=order_type,
                quantity=(
                    order.quantity
                ),
                reference_price=(
                    reference_price
                ),
                limit_price=(
                    order.limit_price
                ),
            )
        )

        order = (
            self._order_repository
            .mark_submitted(
                order,
                broker_order_id=(
                    result.broker_order_id
                ),
                broker_name=(
                    "sandbox"
                ),
            )
        )

        if (
            result.status
            == OrderStatus.ACCEPTED
        ):
            self._audit_repository.create(
                account_id=(
                    account.id
                ),
                order_id=(
                    order.id
                ),
                event_type=(
                    "order_accepted"
                ),
                message=(
                    "Sandbox order was "
                    "accepted without a fill."
                ),
                event_data={
                    "broker_order_id": (
                        result.broker_order_id
                    ),
                    "broker_name": (
                        "sandbox"
                    ),
                    "symbol": (
                        order.symbol
                    ),
                    "side": (
                        order.side
                    ),
                },
            )

            return result

        if not result.fills:
            self._audit_repository.create(
                account_id=(
                    account.id
                ),
                order_id=(
                    order.id
                ),
                event_type=(
                    "order_not_filled"
                ),
                message=(
                    "Sandbox order produced "
                    "no fills."
                ),
                event_data={
                    "broker_order_id": (
                        result.broker_order_id
                    ),
                    "broker_name": (
                        "sandbox"
                    ),
                },
            )

            return result

        total_filled_quantity = 0.0

        total_fill_notional = 0.0

        for fill in result.fills:
            self._apply_fill(
                account=account,
                order=order,
                side=side,
                quantity=(
                    fill.quantity
                ),
                price=(
                    fill.price
                ),
                commission=(
                    fill.commission
                ),
                slippage_cost=(
                    fill.slippage_cost
                ),
            )

            total_filled_quantity += (
                fill.quantity
            )

            total_fill_notional += (
                fill.quantity
                * fill.price
            )

        if total_filled_quantity <= 0:
            raise RuntimeError(
                (
                    "Sandbox execution returned "
                    "fills with zero total "
                    "quantity."
                )
            )

        average_fill_price = (
            total_fill_notional
            / total_filled_quantity
        )

        if (
            result.status
            == OrderStatus.FILLED
        ):
            self._order_repository.update_fill_state(
                order,
                filled_quantity=(
                    total_filled_quantity
                ),
                average_fill_price=(
                    average_fill_price
                ),
                status=(
                    OrderStatus.FILLED
                ),
            )

            event_type = (
                "order_filled"
            )

            message = (
                "Sandbox order was filled."
            )

        elif (
            result.status
            == OrderStatus.PARTIALLY_FILLED
        ):
            self._order_repository.update_fill_state(
                order,
                filled_quantity=(
                    total_filled_quantity
                ),
                average_fill_price=(
                    average_fill_price
                ),
                status=(
                    OrderStatus.PARTIALLY_FILLED
                ),
            )

            event_type = (
                "order_partially_filled"
            )

            message = (
                "Sandbox order was "
                "partially filled."
            )

        else:
            raise ValueError(
                (
                    "Unsupported sandbox "
                    "execution status: "
                    f"{result.status}"
                )
            )

        self._audit_repository.create(
            account_id=(
                account.id
            ),
            order_id=(
                order.id
            ),
            event_type=(
                event_type
            ),
            message=(
                message
            ),
            event_data={
                "broker_order_id": (
                    result.broker_order_id
                ),
                "broker_name": (
                    "sandbox"
                ),
                "symbol": (
                    order.symbol
                ),
                "side": (
                    order.side
                ),
                "filled_quantity": (
                    total_filled_quantity
                ),
                "average_fill_price": (
                    average_fill_price
                ),
            },
        )

        return result

    def _apply_fill(
        self,
        *,
        account,
        order,
        side: OrderSide,
        quantity: float,
        price: float,
        commission: float,
        slippage_cost: float,
    ) -> None:
        notional = (
            quantity
            * price
        )

        self._fill_repository.create(
            order_id=(
                order.id
            ),
            quantity=(
                quantity
            ),
            price=(
                price
            ),
            notional=(
                notional
            ),
            commission=(
                commission
            ),
            slippage_cost=(
                slippage_cost
            ),
        )

        position = (
            self._position_repository
            .get(
                account_id=(
                    account.id
                ),
                instrument_id=(
                    order.instrument_id
                ),
            )
        )

        if position is None:
            position = (
                self._position_repository
                .create(
                    account_id=(
                        account.id
                    ),
                    instrument_id=(
                        order.instrument_id
                    ),
                    symbol=(
                        order.symbol
                    ),
                    quantity=0.0,
                    average_price=0.0,
                )
            )

        signed_fill_quantity = (
            quantity
            if side == OrderSide.BUY
            else -quantity
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
                    signed_fill_quantity
                ),
                fill_price=(
                    price
                ),
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
                - notional
                - commission
            )

        else:
            new_cash = (
                account.cash
                + notional
                - commission
            )

        new_realized_pnl = (
            account.realized_pnl
            + accounting_result.realized_pnl_delta
            - commission
        )

        self._account_repository.update_cash(
            account,
            cash=(
                new_cash
            ),
            realized_pnl=(
                new_realized_pnl
            ),
        )