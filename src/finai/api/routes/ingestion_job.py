from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.ingestion_job import (
    IngestionJobCreate,
    IngestionJobResponse,
)
from finai.application.market_data.ingestion_job_service import (
    execute_ingestion_job,
)
from finai.core.config import get_settings
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.exceptions import (
    InstrumentNotFoundError,
)
from finai.infrastructure.database.repositories.ingestion_job_repository import (
    IngestionJobRepository,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)


router = APIRouter(
    prefix="/api/v1/ingestion-jobs",
    tags=["ingestion-jobs"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_ingestion_job(
    request: IngestionJobCreate,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
) -> IngestionJobResponse:
    instrument_repository = InstrumentRepository(session)

    try:
        instrument_repository.get_model_by_symbol(request.symbol)
    except InstrumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    repository = IngestionJobRepository(session)

    job = repository.create(
        symbol=request.symbol,
        interval=request.interval.value,
        start_time=request.start_time,
        end_time=request.end_time,
    )

    settings = get_settings()

    background_tasks.add_task(
        execute_ingestion_job,
        job.id,
        settings.market_data_provider,
    )

    return IngestionJobResponse.model_validate(job)


@router.get(
    "/{job_id}",
    response_model=IngestionJobResponse,
)
def get_ingestion_job(
    job_id: UUID,
    session: DatabaseSession,
) -> IngestionJobResponse:
    repository = IngestionJobRepository(session)
    job = repository.get_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job '{job_id}' was not found.",
        )

    return IngestionJobResponse.model_validate(job)
