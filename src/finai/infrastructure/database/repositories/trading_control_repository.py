from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.trading_control import (
    TradingControlModel,
)


class TradingControlRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get_for_account(
        self,
        *,
        account_id: UUID,
    ) -> TradingControlModel | None:
        statement = select(
            TradingControlModel
        ).where(
            TradingControlModel.account_id
            == account_id
        )

        return self._session.scalar(
            statement
        )

    def create(
        self,
        *,
        account_id: UUID,
        maximum_daily_loss_fraction: float,
        maximum_gross_exposure_fraction: float,
        maximum_symbol_fraction: float,
        maximum_order_fraction: float,
    ) -> TradingControlModel:
        model = TradingControlModel(
            account_id=account_id,
            trading_enabled=True,
            manual_halt=False,
            circuit_breaker_tripped=False,
            maximum_daily_loss_fraction=(
                maximum_daily_loss_fraction
            ),
            maximum_gross_exposure_fraction=(
                maximum_gross_exposure_fraction
            ),
            maximum_symbol_fraction=(
                maximum_symbol_fraction
            ),
            maximum_order_fraction=(
                maximum_order_fraction
            ),
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def initialize_day(
        self,
        model: TradingControlModel,
        *,
        day: date,
        equity: float,
    ) -> TradingControlModel:
        model.day_start_date = day
        model.day_start_equity = equity
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def set_manual_halt(
        self,
        model: TradingControlModel,
        *,
        reason: str,
    ) -> TradingControlModel:
        model.manual_halt = True
        model.manual_halt_reason = reason
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def clear_manual_halt(
        self,
        model: TradingControlModel,
    ) -> TradingControlModel:
        model.manual_halt = False
        model.manual_halt_reason = None
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def trip_circuit_breaker(
        self,
        model: TradingControlModel,
        *,
        reason: str,
        message: str,
    ) -> TradingControlModel:
        now = datetime.now(UTC)

        model.circuit_breaker_tripped = True
        model.circuit_breaker_reason = reason
        model.circuit_breaker_message = message
        model.circuit_breaker_tripped_at = now
        model.updated_at = now

        self._session.commit()
        self._session.refresh(model)

        return model

    def reset_circuit_breaker(
        self,
        model: TradingControlModel,
    ) -> TradingControlModel:
        model.circuit_breaker_tripped = False
        model.circuit_breaker_reason = None
        model.circuit_breaker_message = None
        model.circuit_breaker_tripped_at = None
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def set_trading_enabled(
        self,
        model: TradingControlModel,
        *,
        enabled: bool,
    ) -> TradingControlModel:
        model.trading_enabled = enabled
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model