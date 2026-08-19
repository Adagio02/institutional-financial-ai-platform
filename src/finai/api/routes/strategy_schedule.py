from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.routes.strategy_run import (
    build_run_service,
)
from finai.api.schemas.strategy_schedule import (
    ScheduleWorkerRequest,
    ScheduleWorkerResultResponse,
    StrategyScheduleCreate,
    StrategyScheduleDetailResponse,
    StrategyScheduleResponse,
    StrategyScheduleSignalResponse,
)
from finai.application.services.strategy_schedule_service import (
    StrategyScheduleService,
)
from finai.application.services.strategy_schedule_worker_service import (
    StrategyScheduleWorkerService,
)
from finai.core.config import (
    get_settings,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.strategy_schedule_repository import (
    StrategyScheduleRepository,
)


router = APIRouter(
    prefix="/api/v1/strategy/schedules",
    tags=["strategy-schedules"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_schedule_service(
    *,
    session: Session,
) -> StrategyScheduleService:
    settings = get_settings()

    return StrategyScheduleService(
        session=session,
        run_service=build_run_service(
            session=session
        ),
        maximum_schedules_per_account=(
            settings
            .strategy_schedule_maximum_per_account
        ),
    )


def build_worker_service(
    *,
    session: Session,
) -> StrategyScheduleWorkerService:
    settings = get_settings()

    return StrategyScheduleWorkerService(
        session=session,
        schedule_service=(
            build_schedule_service(
                session=session
            )
        ),
        lease_seconds=(
            settings
            .strategy_schedule_lease_seconds
        ),
        batch_size=(
            settings
            .strategy_schedule_worker_batch_size
        ),
        retry_base_seconds=(
            settings
            .strategy_schedule_retry_base_seconds
        ),
        retry_maximum_seconds=(
            settings
            .strategy_schedule_retry_maximum_seconds
        ),
        maximum_failures=(
            settings
            .strategy_schedule_maximum_failures
        ),
    )


def build_detail(
    *,
    service: StrategyScheduleService,
    schedule,
) -> StrategyScheduleDetailResponse:
    signals = service.list_signals(
        schedule_id=schedule.id
    )

    base = (
        StrategyScheduleResponse
        .model_validate(schedule)
    )

    return StrategyScheduleDetailResponse(
        **base.model_dump(),
        signals=[
            StrategyScheduleSignalResponse
            .model_validate(signal)
            for signal in signals
        ],
    )


@router.post(
    "",
    response_model=(
        StrategyScheduleDetailResponse
    ),
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    request: StrategyScheduleCreate,
    session: DatabaseSession,
) -> StrategyScheduleDetailResponse:
    service = build_schedule_service(
        session=session
    )

    signals = [
        {
            "symbol": signal.symbol,
            "side": signal.side.value,
            "confidence": signal.confidence,
            "source_model_id": (
                signal.source_model_id
            ),
            "source_prediction_id": (
                signal.source_prediction_id
            ),
        }
        for signal in request.signals
    ]

    try:
        schedule = service.create(
            account_id=request.account_id,
            strategy_key=(
                request.strategy_key
            ),
            name=request.name,
            frequency=request.frequency,
            enabled=request.enabled,
            signals=signals,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(error),
        ) from error

    return build_detail(
        service=service,
        schedule=schedule,
    )


@router.get(
    "/account/{account_id}",
    response_model=list[
        StrategyScheduleResponse
    ],
)
def list_schedules(
    account_id: UUID,
    session: DatabaseSession,
) -> list[StrategyScheduleResponse]:
    repository = (
        StrategyScheduleRepository(
            session
        )
    )

    schedules = (
        repository.list_for_account(
            account_id=account_id
        )
    )

    return [
        StrategyScheduleResponse
        .model_validate(schedule)
        for schedule in schedules
    ]


@router.get(
    "/{schedule_id}",
    response_model=(
        StrategyScheduleDetailResponse
    ),
)
def get_schedule(
    schedule_id: UUID,
    session: DatabaseSession,
) -> StrategyScheduleDetailResponse:
    service = build_schedule_service(
        session=session
    )

    try:
        schedule = service.get(
            schedule_id=schedule_id
        )

    except LookupError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    return build_detail(
        service=service,
        schedule=schedule,
    )


@router.post(
    "/{schedule_id}/enable",
    response_model=(
        StrategyScheduleResponse
    ),
)
def enable_schedule(
    schedule_id: UUID,
    session: DatabaseSession,
) -> StrategyScheduleResponse:
    service = build_schedule_service(
        session=session
    )

    try:
        schedule = service.enable(
            schedule_id=schedule_id
        )

    except LookupError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    return (
        StrategyScheduleResponse
        .model_validate(schedule)
    )


@router.post(
    "/{schedule_id}/disable",
    response_model=(
        StrategyScheduleResponse
    ),
)
def disable_schedule(
    schedule_id: UUID,
    session: DatabaseSession,
) -> StrategyScheduleResponse:
    service = build_schedule_service(
        session=session
    )

    try:
        schedule = service.disable(
            schedule_id=schedule_id
        )

    except LookupError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    return (
        StrategyScheduleResponse
        .model_validate(schedule)
    )


@router.post(
    "/{schedule_id}/run",
)
def run_schedule(
    schedule_id: UUID,
    session: DatabaseSession,
):
    service = build_schedule_service(
        session=session
    )

    try:
        return service.run(
            schedule_id=schedule_id
        )

    except LookupError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(error),
        ) from error


@router.post(
    "/process-due",
    response_model=list[
        ScheduleWorkerResultResponse
    ],
)
def process_due_schedules(
    request: ScheduleWorkerRequest,
    session: DatabaseSession,
) -> list[ScheduleWorkerResultResponse]:
    service = build_worker_service(
        session=session
    )

    try:
        results = service.process_due(
            worker_id=request.worker_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(error),
        ) from error

    return [
        ScheduleWorkerResultResponse(
            schedule_id=result.schedule_id,
            status=result.status,
            strategy_run_id=(
                result.strategy_run_id
            ),
            error_message=(
                result.error_message
            ),
        )
        for result in results
    ]