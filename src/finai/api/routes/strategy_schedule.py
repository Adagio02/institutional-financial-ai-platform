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
    StrategyScheduleCreate,
    StrategyScheduleDetailResponse,
    StrategyScheduleResponse,
    StrategyScheduleSignalResponse,
)
from finai.application.services.strategy_schedule_service import (
    StrategyScheduleService,
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
            settings.strategy_schedule_maximum_per_account
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

    base = StrategyScheduleResponse.model_validate(
        schedule
    )

    return StrategyScheduleDetailResponse(
        **base.model_dump(),
        signals=[
            StrategyScheduleSignalResponse.model_validate(
                signal
            )
            for signal in signals
        ],
    )


@router.post(
    "",
    response_model=StrategyScheduleDetailResponse,
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
            "source_model_id": signal.source_model_id,
            "source_prediction_id": (
                signal.source_prediction_id
            ),
        }
        for signal in request.signals
    ]

    try:
        schedule = service.create(
            account_id=request.account_id,
            strategy_key=request.strategy_key,
            name=request.name,
            frequency=request.frequency,
            enabled=request.enabled,
            signals=signals,
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

    return build_detail(
        service=service,
        schedule=schedule,
    )


@router.get(
    "/account/{account_id}",
    response_model=list[StrategyScheduleResponse],
)
def list_schedules(
    account_id: UUID,
    session: DatabaseSession,
) -> list[StrategyScheduleResponse]:
    repository = StrategyScheduleRepository(
        session
    )

    return [
        StrategyScheduleResponse.model_validate(
            schedule
        )
        for schedule in repository.list_for_account(
            account_id=account_id
        )
    ]


@router.get(
    "/{schedule_id}",
    response_model=StrategyScheduleDetailResponse,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return build_detail(
        service=service,
        schedule=schedule,
    )


@router.post(
    "/{schedule_id}/enable",
    response_model=StrategyScheduleResponse,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return StrategyScheduleResponse.model_validate(
        schedule
    )


@router.post(
    "/{schedule_id}/disable",
    response_model=StrategyScheduleResponse,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return StrategyScheduleResponse.model_validate(
        schedule
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/run-due",
)
def run_due_schedules(
    session: DatabaseSession,
):
    service = build_schedule_service(
        session=session
    )

    return service.run_due()