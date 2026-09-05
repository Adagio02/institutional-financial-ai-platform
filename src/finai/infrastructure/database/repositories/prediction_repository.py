from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.prediction import (
    PredictionModel,
)


class PredictionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        model_id: UUID,
        dataset_id: UUID,
        instrument_id: UUID,
        symbol: str,
        prediction_timestamp: datetime,
        forecast_horizon: str,
        raw_prediction: float,
        probability: float | None,
        confidence: float | None,
        feature_values: dict[str, float],
        model_hash: str,
    ) -> PredictionModel:
        prediction = PredictionModel(
            model_id=model_id,
            dataset_id=dataset_id,
            instrument_id=instrument_id,
            symbol=symbol.strip().upper(),
            prediction_timestamp=prediction_timestamp,
            forecast_horizon=forecast_horizon,
            raw_prediction=raw_prediction,
            probability=probability,
            confidence=confidence,
            feature_values=feature_values,
            model_hash=model_hash,
            status="completed",
        )

        self._session.add(prediction)
        self._session.commit()
        self._session.refresh(prediction)

        return prediction

    def get_by_id(
        self,
        prediction_id: UUID,
    ) -> PredictionModel | None:
        return self._session.get(
            PredictionModel,
            prediction_id,
        )

    def list_all(
        self,
        *,
        limit: int = 100,
    ) -> list[PredictionModel]:
        statement = select(PredictionModel).order_by(PredictionModel.created_at.desc()).limit(limit)

        return list(self._session.scalars(statement))
