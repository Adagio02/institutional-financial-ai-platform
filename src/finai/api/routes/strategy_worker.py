from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from finai.api.schemas.strategy_worker import (
    StrategyWorkerHealthResponse,
    StrategyWorkerResponse,
)
from finai.application.services.strategy_worker_registry_service import (
    StrategyWorkerRegistryService,
)
from finai.core.config import (
    get_settings,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)


router = APIRouter(
    prefix="/api/v1/strategy/workers",
    tags=["strategy-workers"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_registry_service(
    *,
    session: Session,
) -> StrategyWorkerRegistryService:
    settings = get_settings()

    return StrategyWorkerRegistryService(
        session=session,
        stale_after_seconds=(
            settings
            .strategy_scheduler_worker_stale_seconds
        ),
    )


@router.get(
    "",
    response_model=list[
        StrategyWorkerResponse
    ],
)
def list_strategy_workers(
    session: DatabaseSession,
) -> list[StrategyWorkerResponse]:
    service = build_registry_service(
        session=session
    )

    workers = service.list_workers(
        now=datetime.now(UTC)
    )

    return [
        StrategyWorkerResponse.model_validate(
            worker
        )
        for worker in workers
    ]


@router.get(
    "/health",
    response_model=(
        StrategyWorkerHealthResponse
    ),
)
def strategy_worker_health(
    session: DatabaseSession,
) -> StrategyWorkerHealthResponse:
    service = build_registry_service(
        session=session
    )

    workers = service.list_workers(
        now=datetime.now(UTC)
    )

    running = sum(
        worker.status == "running"
        for worker in workers
    )

    stale = sum(
        worker.status == "stale"
        for worker in workers
    )

    failed = sum(
        worker.status == "failed"
        for worker in workers
    )

    return StrategyWorkerHealthResponse(
    total_workers=len(workers),
    running_workers=running,
    stale_workers=stale,
    failed_workers=failed,
    healthy=(running > 0),
)
    