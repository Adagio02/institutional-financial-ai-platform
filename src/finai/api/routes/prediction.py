from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.prediction import (
    PredictionCreate,
    PredictionResponse,
)
from finai.application.services.prediction_service import (
    PredictionService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.prediction_repository import (
    PredictionRepository,
)


router = APIRouter(
    prefix="/api/v1/predictions",
    tags=["predictions"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_prediction(
    request: PredictionCreate,
    session: DatabaseSession,
) -> PredictionResponse:
    service = PredictionService(session=session)

    try:
        prediction = service.predict(
            model_id=request.model_id,
            dataset_id=request.dataset_id,
            symbol=request.symbol,
            prediction_timestamp=(request.prediction_timestamp),
            forecast_horizon=(request.forecast_horizon),
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        ValueError,
        FileNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return PredictionResponse.model_validate(prediction)


@router.get(
    "",
    response_model=list[PredictionResponse],
)
def list_predictions(
    session: DatabaseSession,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> list[PredictionResponse]:
    repository = PredictionRepository(session)

    return [
        PredictionResponse.model_validate(prediction)
        for prediction in repository.list_all(limit=limit)
    ]


@router.get(
    "/{prediction_id}",
    response_model=PredictionResponse,
)
def get_prediction(
    prediction_id: UUID,
    session: DatabaseSession,
) -> PredictionResponse:
    repository = PredictionRepository(session)

    prediction = repository.get_by_id(prediction_id)

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Prediction not found: {prediction_id}"),
        )

    return PredictionResponse.model_validate(prediction)
