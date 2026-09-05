from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.portfolio_snapshot import (
    PortfolioSnapshotModel,
)


class PortfolioSnapshotRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create_many(
        self,
        *,
        snapshots: list[dict],
    ) -> int:
        if not snapshots:
            return 0

        models = [PortfolioSnapshotModel(**snapshot) for snapshot in snapshots]

        self._session.add_all(models)
        self._session.commit()

        return len(models)

    def list_for_backtest(
        self,
        backtest_run_id: UUID,
    ) -> list[PortfolioSnapshotModel]:
        statement = (
            select(PortfolioSnapshotModel)
            .where(PortfolioSnapshotModel.backtest_run_id == backtest_run_id)
            .order_by(PortfolioSnapshotModel.timestamp)
        )

        return list(self._session.scalars(statement))
