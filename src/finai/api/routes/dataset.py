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

from finai.api.schemas.dataset import (
    DatasetBuildRequest,
    DatasetBuildResponse,
    DatasetVersionResponse,
)
from finai.application.services.dataset_builder_service import (
    DatasetBuilderService,
)
from finai.core.config import get_settings
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.dataset_version_repository import (
    DatasetVersionRepository,
)


router = APIRouter(
    prefix="/api/v1/datasets",
    tags=["datasets"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "/build",
    response_model=DatasetBuildResponse,
    status_code=status.HTTP_201_CREATED,
)
def build_dataset(
    request: DatasetBuildRequest,
    session: DatabaseSession,
) -> DatasetBuildResponse:
    settings = get_settings()

    service = DatasetBuilderService(
        session=session,
        output_directory=Path(settings.dataset_output_directory),
    )

    result = service.build(
        name=request.name,
        feature_set_id=request.feature_set_id,
        symbol=request.symbol,
        interval=request.interval,
        start_time=request.start_time,
        end_time=request.end_time,
        drop_missing_rows=(request.drop_missing_rows),
    )

    return DatasetBuildResponse(
        dataset_id=result.dataset_id,
        name=result.name,
        version=result.version,
        row_count=result.row_count,
        schema_hash=result.schema_hash,
        content_hash=result.content_hash,
        storage_uri=result.storage_uri,
    )


@router.get(
    "",
    response_model=list[DatasetVersionResponse],
)
def list_datasets(
    session: DatabaseSession,
) -> list[DatasetVersionResponse]:
    repository = DatasetVersionRepository(session)

    return [DatasetVersionResponse.model_validate(model) for model in repository.list_all()]


@router.get(
    "/{dataset_id}",
    response_model=DatasetVersionResponse,
)
def get_dataset(
    dataset_id: UUID,
    session: DatabaseSession,
) -> DatasetVersionResponse:
    repository = DatasetVersionRepository(session)

    dataset = repository.get_by_id(dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=(f"Dataset not found: {dataset_id}"),
        )

    return DatasetVersionResponse.model_validate(dataset)
