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
)
from finai.api.schemas.model_governance import (
    ModelCardCreate,
    ModelCardResponse,
    ProductionEvaluationResponse,
)
from finai.application.services.model_governance_service import (
    ModelGovernanceService,
)
from finai.core.config import get_settings
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.model_card_repository import (
    ModelCardRepository,
)


router = APIRouter(
    prefix="/api/v1/models",
    tags=["model-governance"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "/{model_id}/card",
    response_model=ModelCardResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_model_card(
    model_id: UUID,
    request: ModelCardCreate,
    session: DatabaseSession,
) -> ModelCardResponse:
    service = ModelGovernanceService(session=session)

    try:
        card = service.create_model_card(
            model_id=model_id,
            summary=request.summary,
            intended_use=request.intended_use,
            limitations=request.limitations,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return ModelCardResponse.model_validate(card)


@router.get(
    "/{model_id}/card",
    response_model=ModelCardResponse,
)
def get_model_card(
    model_id: UUID,
    session: DatabaseSession,
) -> ModelCardResponse:
    repository = ModelCardRepository(session)

    card = repository.get_for_model(model_id)

    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Model card not found for model: {model_id}"),
        )

    return ModelCardResponse.model_validate(card)


@router.post(
    "/{model_id}/production-evaluation",
    response_model=ProductionEvaluationResponse,
)
def evaluate_for_production(
    model_id: UUID,
    session: DatabaseSession,
) -> ProductionEvaluationResponse:
    settings = get_settings()

    service = ModelGovernanceService(session=session)

    try:
        result = service.evaluate_for_production(
            model_id=model_id,
            minimum_accuracy=(settings.governance_minimum_accuracy),
            minimum_r_squared=(settings.governance_minimum_r_squared),
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return ProductionEvaluationResponse(
        model_id=model_id,
        **result,
    )


@router.post(
    "/{model_id}/promote-production",
    response_model=ModelArtifactResponse,
)
def promote_to_production(
    model_id: UUID,
    session: DatabaseSession,
) -> ModelArtifactResponse:
    settings = get_settings()

    service = ModelGovernanceService(session=session)

    try:
        model = service.promote_to_production(
            model_id=model_id,
            minimum_accuracy=(settings.governance_minimum_accuracy),
            minimum_r_squared=(settings.governance_minimum_r_squared),
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return ModelArtifactResponse.model_validate(model)
