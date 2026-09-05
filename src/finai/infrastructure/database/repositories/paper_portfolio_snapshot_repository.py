from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.paper_portfolio_snapshot import (
    PaperPortfolioSnapshotModel,
)


class PaperPortfolioSnapshotRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        account_id: UUID,
        cash: float,
        gross_exposure: float,
        net_exposure: float,
        equity: float,
        realized_pnl: float,
        unrealized_pnl: float,
    ) -> PaperPortfolioSnapshotModel:
        snapshot = PaperPortfolioSnapshotModel(
            account_id=account_id,
            cash=cash,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            equity=equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
        )

        self._session.add(snapshot)
        self._session.commit()
        self._session.refresh(snapshot)

        return snapshot

    def list_for_account(
        self,
        account_id: UUID,
        *,
        limit: int = 500,
    ) -> list[PaperPortfolioSnapshotModel]:
        statement = (
            select(PaperPortfolioSnapshotModel)
            .where(PaperPortfolioSnapshotModel.account_id == account_id)
            .order_by(PaperPortfolioSnapshotModel.created_at.desc())
            .limit(limit)
        )

        return list(self._session.scalars(statement))
