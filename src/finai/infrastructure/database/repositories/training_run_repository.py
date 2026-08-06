from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.training_run import (
    TrainingRunModel,
)


class TrainingRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        dataset_id: UUID,
        model_type: str,
        prediction_task: str,
        target_column: str,
        feature_columns: list[str],
        parameters: dict,
        number_of_splits: int,
        test_size: int,
        random_seed: int,
    ) -> TrainingRunModel:
        run = TrainingRunModel(
            dataset_id=dataset_id,
            model_type=model_type,
            prediction_task=prediction_task,
            target_column=target_column,
            feature_columns=feature_columns,
            parameters=parameters,
            number_of_splits=number_of_splits,
            test_size=test_size,
            random_seed=random_seed,
            status="pending",
        )

        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)

        return run

    def get_by_id(
        self,
        run_id: UUID,
    ) -> TrainingRunModel | None:
        return self._session.get(
            TrainingRunModel,
            run_id,
        )

    def list_all(
        self,
    ) -> list[TrainingRunModel]:
        statement = select(TrainingRunModel).order_by(TrainingRunModel.created_at.desc())

        return list(self._session.scalars(statement))

    def mark_running(
        self,
        run: TrainingRunModel,
    ) -> TrainingRunModel:
        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.error_message = None

        self._session.commit()
        self._session.refresh(run)

        return run

    def mark_completed(
        self,
        run: TrainingRunModel,
        *,
        mlflow_run_id: str | None,
    ) -> TrainingRunModel:
        run.status = "completed"
        run.mlflow_run_id = mlflow_run_id
        run.completed_at = datetime.now(UTC)
        run.error_message = None

        self._session.commit()
        self._session.refresh(run)

        return run

    def mark_failed(
        self,
        run: TrainingRunModel,
        *,
        error_message: str,
    ) -> TrainingRunModel:
        run.status = "failed"
        run.error_message = error_message[:4000]
        run.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(run)

        return run
