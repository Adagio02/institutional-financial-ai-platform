from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.paper_account import (
    PaperAccountModel,
)


class PaperAccountRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        initial_cash: float,
        base_currency: str = "USD",
    ) -> PaperAccountModel:
        account = PaperAccountModel(
            name=name,
            initial_cash=initial_cash,
            cash=initial_cash,
            base_currency=base_currency,
        )

        self._session.add(account)
        self._session.commit()
        self._session.refresh(account)

        return account

    def get_by_id(
        self,
        account_id: UUID,
    ) -> PaperAccountModel | None:
        return self._session.get(
            PaperAccountModel,
            account_id,
        )

    def list_all(
        self,
    ) -> list[PaperAccountModel]:
        statement = select(PaperAccountModel).order_by(PaperAccountModel.created_at.desc())

        return list(self._session.scalars(statement))

    def update_cash(
        self,
        account: PaperAccountModel,
        *,
        cash: float,
        realized_pnl: float | None = None,
    ) -> PaperAccountModel:
        account.cash = cash

        if realized_pnl is not None:
            account.realized_pnl = realized_pnl

        self._session.commit()
        self._session.refresh(account)

        return account
