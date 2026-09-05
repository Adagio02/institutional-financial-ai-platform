from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.prediction_explanation import (
    PredictionExplanationModel,
)


class PredictionExplanationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        prediction_id: UUID,
        explanation_type: str,
        baseline_value: float | None,
        contributions: dict[str, float],
        metadata_json: dict,
    ) -> PredictionExplanationModel:
        explanation = PredictionExplanationModel(
            prediction_id=prediction_id,
            explanation_type=explanation_type,
            baseline_value=baseline_value,
            contributions=contributions,
            metadata_json=metadata_json,
        )

        self._session.add(explanation)
        self._session.commit()
        self._session.refresh(explanation)

        return explanation

    def list_for_prediction(
        self,
        prediction_id: UUID,
    ) -> list[PredictionExplanationModel]:
        statement = (
            select(PredictionExplanationModel)
            .where(PredictionExplanationModel.prediction_id == prediction_id)
            .order_by(PredictionExplanationModel.created_at)
        )

        return list(self._session.scalars(statement))
