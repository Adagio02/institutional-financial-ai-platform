from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.paper_position import (
    PaperPositionModel,
)


class PaperPositionRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get(
        self,
        *,
        account_id: UUID,
        instrument_id: UUID,
    ) -> PaperPositionModel | None:
        statement = select(PaperPositionModel).where(
            PaperPositionModel.account_id == account_id,
            PaperPositionModel.instrument_id == instrument_id,
        )

        return self._session.scalar(statement)

    def list_for_account(
        self,
        account_id: UUID,
    ) -> list[PaperPositionModel]:
        statement = (
            select(PaperPositionModel)
            .where(PaperPositionModel.account_id == account_id)
            .order_by(PaperPositionModel.symbol)
        )

        return list(self._session.scalars(statement))

    def save(
        self,
        position: PaperPositionModel,
    ) -> PaperPositionModel:
        self._session.add(position)
        self._session.commit()
        self._session.refresh(position)

        return position

    def create(
        self,
        *,
        account_id: UUID,
        instrument_id: UUID,
        symbol: str,
        quantity: float,
        average_price: float,
    ) -> PaperPositionModel:
        position = PaperPositionModel(
            account_id=account_id,
            instrument_id=instrument_id,
            symbol=symbol,
            quantity=quantity,
            average_price=average_price,
        )

        return self.save(position)
