from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from finai.domain.risk.trading_control import (
    TradingControlDecision,
    evaluate_trading_controls,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.trading_control_repository import (
    TradingControlRepository,
)


class TradingControlService:
    def __init__(
        self,
        *,
        session: Session,
        default_maximum_daily_loss_fraction: float,
        default_maximum_gross_exposure_fraction: float,
        default_maximum_symbol_fraction: float,
        default_maximum_order_fraction: float,
    ) -> None:
        self._account_repository = (
            PaperAccountRepository(
                session
            )
        )

        self._repository = (
            TradingControlRepository(
                session
            )
        )

        self._default_maximum_daily_loss_fraction = (
            default_maximum_daily_loss_fraction
        )

        self._default_maximum_gross_exposure_fraction = (
            default_maximum_gross_exposure_fraction
        )

        self._default_maximum_symbol_fraction = (
            default_maximum_symbol_fraction
        )

        self._default_maximum_order_fraction = (
            default_maximum_order_fraction
        )

    def ensure_for_account(
        self,
        *,
        account_id: UUID,
    ):
        account = (
            self._account_repository.get_by_id(
                account_id
            )
        )

        if account is None:
            raise LookupError(
                f"Paper account not found: {account_id}"
            )

        control = (
            self._repository.get_for_account(
                account_id=account_id
            )
        )

        if control is not None:
            return control

        return self._repository.create(
            account_id=account_id,
            maximum_daily_loss_fraction=(
                self._default_maximum_daily_loss_fraction
            ),
            maximum_gross_exposure_fraction=(
                self._default_maximum_gross_exposure_fraction
            ),
            maximum_symbol_fraction=(
                self._default_maximum_symbol_fraction
            ),
            maximum_order_fraction=(
                self._default_maximum_order_fraction
            ),
        )

    def prepare_day(
        self,
        *,
        account_id: UUID,
        current_equity: float,
    ):
        control = self.ensure_for_account(
            account_id=account_id
        )

        today = datetime.now(UTC).date()

        if (
            control.day_start_date != today
            or control.day_start_equity is None
        ):
            control = self._repository.initialize_day(
                control,
                day=today,
                equity=current_equity,
            )

        return control

    def evaluate(
        self,
        *,
        account_id: UUID,
        current_equity: float,
        current_gross_exposure: float,
        current_symbol_exposure: float,
        proposed_order_notional: float,
    ) -> TradingControlDecision:
        control = self.prepare_day(
            account_id=account_id,
            current_equity=current_equity,
        )

        decision = evaluate_trading_controls(
            trading_enabled=(
                control.trading_enabled
            ),
            manual_halt=(
                control.manual_halt
            ),
            circuit_breaker_tripped=(
                control.circuit_breaker_tripped
            ),
            account_equity=current_equity,
            day_start_equity=(
                control.day_start_equity
                if control.day_start_equity is not None
                else current_equity
            ),
            current_gross_exposure=(
                current_gross_exposure
            ),
            current_symbol_exposure=(
                current_symbol_exposure
            ),
            proposed_order_notional=(
                proposed_order_notional
            ),
            maximum_daily_loss_fraction=(
                control.maximum_daily_loss_fraction
            ),
            maximum_gross_exposure_fraction=(
                control.maximum_gross_exposure_fraction
            ),
            maximum_symbol_fraction=(
                control.maximum_symbol_fraction
            ),
            maximum_order_fraction=(
                control.maximum_order_fraction
            ),
        )

        if (
            not decision.approved
            and decision.reason is not None
            and decision.reason.value
            not in {
                "manual_halt",
                "trading_disabled",
            }
        ):
            self._repository.trip_circuit_breaker(
                control,
                reason=decision.reason.value,
                message=(
                    decision.message
                    or "Circuit breaker triggered."
                ),
            )

        return decision

    def halt(
        self,
        *,
        account_id: UUID,
        reason: str,
    ):
        normalized_reason = reason.strip()

        if not normalized_reason:
            raise ValueError(
                "Halt reason cannot be blank."
            )

        control = self.ensure_for_account(
            account_id=account_id
        )

        return self._repository.set_manual_halt(
            control,
            reason=normalized_reason,
        )

    def resume(
        self,
        *,
        account_id: UUID,
    ):
        control = self.ensure_for_account(
            account_id=account_id
        )

        control = (
            self._repository.clear_manual_halt(
                control
            )
        )

        return control

    def reset_circuit_breaker(
        self,
        *,
        account_id: UUID,
    ):
        control = self.ensure_for_account(
            account_id=account_id
        )

        return (
            self._repository.reset_circuit_breaker(
                control
            )
        )

    def set_enabled(
        self,
        *,
        account_id: UUID,
        enabled: bool,
    ):
        control = self.ensure_for_account(
            account_id=account_id
        )

        return (
            self._repository.set_trading_enabled(
                control,
                enabled=enabled,
            )
        )