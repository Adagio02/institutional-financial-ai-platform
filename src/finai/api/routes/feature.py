from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.feature import (
    FeatureGenerationRequest,
    FeatureGenerationResponse,
    FeatureSetResponse,
)
from finai.application.services.feature_engineering_service import (
    FeatureEngineeringService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.feature_set_repository import (
    FeatureSetRepository,
)


router = APIRouter(
    prefix="/api/v1/features",
    tags=["features"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "/generate",
    response_model=FeatureGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_features(
    request: FeatureGenerationRequest,
    session: DatabaseSession,
) -> FeatureGenerationResponse:
    service = FeatureEngineeringService(session=session)

    feature_set, persisted_count = service.generate(
        feature_set_name=(request.feature_set_name),
        description=request.description,
        configuration=(request.configuration),
        symbol=request.symbol,
        interval=request.interval,
        start_time=request.start_time,
        end_time=request.end_time,
    )

    return FeatureGenerationResponse(
        feature_set_id=feature_set.id,
        name=feature_set.name,
        version=feature_set.version,
        values_persisted=persisted_count,
    )


@router.get(
    "/sets",
    response_model=list[FeatureSetResponse],
)
def list_feature_sets(
    session: DatabaseSession,
) -> list[FeatureSetResponse]:
    repository = FeatureSetRepository(session)

    return [FeatureSetResponse.model_validate(model) for model in repository.list_all()]
