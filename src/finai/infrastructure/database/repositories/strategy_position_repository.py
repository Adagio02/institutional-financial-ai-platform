from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.strategy_position import (
    StrategyPositionModel,
)


class StrategyPositionRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        instrument_id: UUID,
    ) -> StrategyPositionModel | None:
        statement = select(StrategyPositionModel).where(
            StrategyPositionModel.account_id == account_id,
            StrategyPositionModel.strategy_key == strategy_key,
            StrategyPositionModel.instrument_id == instrument_id,
        )

        return self._session.scalar(statement)

    def get_or_create(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        instrument_id: UUID,
        symbol: str,
    ) -> StrategyPositionModel:
        existing = self.get(
            account_id=account_id,
            strategy_key=strategy_key,
            instrument_id=instrument_id,
        )

        if existing is not None:
            return existing

        model = StrategyPositionModel(
            account_id=account_id,
            strategy_key=strategy_key,
            instrument_id=instrument_id,
            symbol=symbol,
            quantity=0.0,
            average_price=0.0,
            realized_pnl=0.0,
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def list_for_strategy(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
    ) -> list[StrategyPositionModel]:
        statement = select(StrategyPositionModel).where(
            StrategyPositionModel.account_id == account_id,
            StrategyPositionModel.strategy_key == strategy_key,
        )

        return list(self._session.scalars(statement).all())

    def save(
        self,
        position: StrategyPositionModel,
    ) -> StrategyPositionModel:
        self._session.add(position)
        self._session.commit()
        self._session.refresh(position)

        return position
