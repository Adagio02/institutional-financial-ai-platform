from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.strategy_schedule_signal import (
    StrategyScheduleSignalModel,
)


class StrategyScheduleSignalRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create_many(
        self,
        *,
        schedule_id: UUID,
        signals: list[dict],
    ) -> list[StrategyScheduleSignalModel]:
        models: list[StrategyScheduleSignalModel] = []

        for sequence_number, signal in enumerate(
            signals,
            start=1,
        ):
            model = StrategyScheduleSignalModel(
                schedule_id=schedule_id,
                sequence_number=sequence_number,
                symbol=signal["symbol"].strip().upper(),
                side=signal["side"],
                confidence=signal["confidence"],
                source_model_id=signal.get(
                    "source_model_id"
                ),
                source_prediction_id=signal.get(
                    "source_prediction_id"
                ),
            )

            self._session.add(model)
            models.append(model)

        self._session.commit()

        for model in models:
            self._session.refresh(model)

        return models

    def list_for_schedule(
        self,
        *,
        schedule_id: UUID,
    ) -> list[StrategyScheduleSignalModel]:
        statement = (
            select(StrategyScheduleSignalModel)
            .where(
                StrategyScheduleSignalModel.schedule_id
                == schedule_id
            )
            .order_by(
                StrategyScheduleSignalModel.sequence_number
            )
        )

        return list(
            self._session.scalars(statement).all()
        )