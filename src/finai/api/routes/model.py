from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.model import (
    ModelArtifactResponse,
    ModelStageUpdate,
)
from finai.application.services.model_registry_service import (
    ModelRegistryService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.model_artifact_repository import (
    ModelArtifactRepository,
)


router = APIRouter(
    prefix="/api/v1/models",
    tags=["models"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.get(
    "",
    response_model=list[ModelArtifactResponse],
)
def list_models(
    session: DatabaseSession,
) -> list[ModelArtifactResponse]:
    repository = ModelArtifactRepository(session)

    return [ModelArtifactResponse.model_validate(model) for model in repository.list_all()]


@router.get(
    "/{model_id}",
    response_model=ModelArtifactResponse,
)
def get_model(
    model_id: UUID,
    session: DatabaseSession,
) -> ModelArtifactResponse:
    repository = ModelArtifactRepository(session)

    model = repository.get_by_id(model_id)

    if model is None:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=f"Model not found: {model_id}",
        )

    return ModelArtifactResponse.model_validate(model)


@router.post(
    "/{model_id}/stage",
    response_model=ModelArtifactResponse,
)
def update_model_stage(
    model_id: UUID,
    request: ModelStageUpdate,
    session: DatabaseSession,
) -> ModelArtifactResponse:
    service = ModelRegistryService(session=session)

    try:
        model = service.update_stage(
            model_id=model_id,
            stage=request.stage,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(error),
        ) from error

    return ModelArtifactResponse.model_validate(model)
