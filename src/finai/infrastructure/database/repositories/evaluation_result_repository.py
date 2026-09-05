from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.evaluation_result import (
    EvaluationResultModel,
)


class EvaluationResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        training_run_id: UUID,
        fold_number: int | None,
        metrics: dict[str, float],
        training_rows: int,
        validation_rows: int,
    ) -> EvaluationResultModel:
        result = EvaluationResultModel(
            training_run_id=training_run_id,
            fold_number=fold_number,
            metrics=metrics,
            training_rows=training_rows,
            validation_rows=validation_rows,
        )

        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)

        return result

    def list_for_run(
        self,
        training_run_id: UUID,
    ) -> list[EvaluationResultModel]:
        statement = (
            select(EvaluationResultModel)
            .where(EvaluationResultModel.training_run_id == training_run_id)
            .order_by(EvaluationResultModel.fold_number)
        )

        return list(self._session.scalars(statement))
