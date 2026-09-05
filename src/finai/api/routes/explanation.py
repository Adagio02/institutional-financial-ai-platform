from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.explanation import (
    PredictionExplanationResponse,
)
from finai.application.services.explanation_service import (
    ExplanationService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.prediction_explanation_repository import (
    PredictionExplanationRepository,
)


router = APIRouter(
    prefix="/api/v1/predictions",
    tags=["explanations"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "/{prediction_id}/explanations",
    response_model=PredictionExplanationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_explanation(
    prediction_id: UUID,
    session: DatabaseSession,
) -> PredictionExplanationResponse:
    service = ExplanationService(session=session)

    try:
        explanation = service.explain(prediction_id=prediction_id)
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

    return PredictionExplanationResponse.model_validate(explanation)


@router.get(
    "/{prediction_id}/explanations",
    response_model=list[PredictionExplanationResponse],
)
def list_explanations(
    prediction_id: UUID,
    session: DatabaseSession,
) -> list[PredictionExplanationResponse]:
    repository = PredictionExplanationRepository(session)

    return [
        PredictionExplanationResponse.model_validate(explanation)
        for explanation in repository.list_for_prediction(prediction_id)
    ]
