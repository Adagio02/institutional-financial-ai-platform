from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.trading_control import (
    TradingControlModel,
)


GLOBAL_CONTROL_KEY = "global"


class TradingControlRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get_global(
        self,
    ) -> TradingControlModel | None:
        statement = select(TradingControlModel).where(
            TradingControlModel.control_key == GLOBAL_CONTROL_KEY
        )

        return self._session.scalar(statement)

    def get_or_create_global(
        self,
    ) -> TradingControlModel:
        control = self.get_global()

        if control is not None:
            return control

        control = TradingControlModel(
            control_key=GLOBAL_CONTROL_KEY,
            trading_enabled=True,
            kill_switch_active=False,
            reason=None,
        )

        self._session.add(control)
        self._session.commit()
        self._session.refresh(control)

        return control

    def save(
        self,
        control: TradingControlModel,
    ) -> TradingControlModel:
        self._session.add(control)
        self._session.commit()
        self._session.refresh(control)

        return control
