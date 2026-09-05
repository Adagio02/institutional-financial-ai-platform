from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.simulated_trade import (
    SimulatedTradeModel,
)


class SimulatedTradeRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create_many(
        self,
        *,
        trades: list[dict],
    ) -> int:
        if not trades:
            return 0

        models = [SimulatedTradeModel(**trade) for trade in trades]

        self._session.add_all(models)
        self._session.commit()

        return len(models)

    def list_for_backtest(
        self,
        backtest_run_id: UUID,
    ) -> list[SimulatedTradeModel]:
        statement = (
            select(SimulatedTradeModel)
            .where(SimulatedTradeModel.backtest_run_id == backtest_run_id)
            .order_by(SimulatedTradeModel.timestamp)
        )

        return list(self._session.scalars(statement))
