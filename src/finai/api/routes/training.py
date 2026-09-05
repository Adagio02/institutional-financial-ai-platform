from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.training import (
    TrainingExecutionResponse,
    TrainingRunCreate,
    TrainingRunResponse,
)
from finai.application.services.training_service import (
    TrainingService,
)
from finai.core.config import get_settings
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.training_run_repository import (
    TrainingRunRepository,
)


router = APIRouter(
    prefix="/api/v1/training/runs",
    tags=["training"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "",
    response_model=TrainingExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_training_run(
    request: TrainingRunCreate,
    session: DatabaseSession,
) -> TrainingExecutionResponse:
    settings = get_settings()

    service = TrainingService(
        session=session,
        model_output_directory=Path(settings.model_output_directory),
        mlflow_tracking_uri=(settings.mlflow_tracking_uri),
        mlflow_experiment_name=(settings.mlflow_experiment_name),
    )

    run, artifact, metrics = service.train(
        dataset_id=request.dataset_id,
        model_type=request.model_type,
        prediction_task=(request.prediction_task),
        feature_columns=(request.feature_columns),
        parameters=request.parameters,
        number_of_splits=(request.number_of_splits),
        test_size=request.test_size,
        random_seed=request.random_seed,
    )

    return TrainingExecutionResponse(
        training_run=(TrainingRunResponse.model_validate(run)),
        model_artifact_id=artifact.id,
        metrics=metrics,
    )


@router.get(
    "",
    response_model=list[TrainingRunResponse],
)
def list_training_runs(
    session: DatabaseSession,
) -> list[TrainingRunResponse]:
    repository = TrainingRunRepository(session)

    return [TrainingRunResponse.model_validate(run) for run in repository.list_all()]


@router.get(
    "/{run_id}",
    response_model=TrainingRunResponse,
)
def get_training_run(
    run_id: UUID,
    session: DatabaseSession,
) -> TrainingRunResponse:
    repository = TrainingRunRepository(session)

    run = repository.get_by_id(run_id)

    if run is None:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=f"Training run not found: {run_id}",
        )

    return TrainingRunResponse.model_validate(run)
