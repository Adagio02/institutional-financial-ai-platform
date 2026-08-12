from sqlalchemy.orm import Session

from finai.domain.execution.control import (
    TradingControlState,
    validate_trading_control,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.trading_control_repository import (
    TradingControlRepository,
)


class TradingControlService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._repository = TradingControlRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

    def get_state(
        self,
    ) -> TradingControlState:
        control = self._repository.get_or_create_global()

        return TradingControlState(
            trading_enabled=(control.trading_enabled),
            kill_switch_active=(control.kill_switch_active),
            reason=control.reason,
        )

    def assert_trading_allowed(
        self,
    ) -> None:
        state = self.get_state()

        if not state.trading_enabled:
            raise ValueError("Paper trading is disabled.")

        if state.kill_switch_active:
            raise ValueError("Trading kill switch is active.")

    def set_trading_enabled(
        self,
        *,
        enabled: bool,
        reason: str | None = None,
    ) -> TradingControlState:
        control = self._repository.get_or_create_global()

        if enabled and control.kill_switch_active:
            raise ValueError("Cannot enable trading while the kill switch is active.")

        validate_trading_control(
            trading_enabled=enabled,
            kill_switch_active=(control.kill_switch_active),
            reason=reason,
        )

        control.trading_enabled = enabled
        control.reason = reason

        self._repository.save(control)

        self._audit_repository.create(
            event_type=("trading_enabled" if enabled else "trading_disabled"),
            message=("Global paper trading state was changed."),
            event_data={
                "enabled": enabled,
                "reason": reason,
            },
        )

        return self.get_state()

    def activate_kill_switch(
        self,
        *,
        reason: str,
    ) -> TradingControlState:
        normalized_reason = reason.strip()

        if not normalized_reason:
            raise ValueError("Kill-switch reason is required.")

        control = self._repository.get_or_create_global()

        control.kill_switch_active = True
        control.trading_enabled = False
        control.reason = normalized_reason

        self._repository.save(control)

        self._audit_repository.create(
            event_type="kill_switch_activated",
            message=("Global trading kill switch was activated."),
            event_data={"reason": normalized_reason},
        )

        return self.get_state()

    def deactivate_kill_switch(
        self,
        *,
        reason: str,
    ) -> TradingControlState:
        normalized_reason = reason.strip()

        if not normalized_reason:
            raise ValueError("A reason is required to deactivate the kill switch.")

        control = self._repository.get_or_create_global()

        control.kill_switch_active = False
        control.trading_enabled = False
        control.reason = normalized_reason

        self._repository.save(control)

        self._audit_repository.create(
            event_type=("kill_switch_deactivated"),
            message=("Global trading kill switch was deactivated."),
            event_data={"reason": normalized_reason},
        )

        return self.get_state()
