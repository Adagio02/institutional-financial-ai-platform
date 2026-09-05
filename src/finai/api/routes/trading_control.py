from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.trading_control import (
    TradingControlResponse,
    TradingEnabledRequest,
    TradingHaltRequest,
)
from finai.application.services.trading_control_service import (
    TradingControlService,
)
from finai.core.config import (
    get_settings,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)


router = APIRouter(
    prefix="/api/v1/trading-controls",
    tags=["trading-controls"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_trading_control_service(
    *,
    session: Session,
) -> TradingControlService:
    settings = get_settings()

    return TradingControlService(
        session=session,
        default_maximum_daily_loss_fraction=(
            settings
            .trading_control_maximum_daily_loss_fraction
        ),
        default_maximum_gross_exposure_fraction=(
            settings
            .trading_control_maximum_gross_exposure_fraction
        ),
        default_maximum_symbol_fraction=(
            settings
            .trading_control_maximum_symbol_fraction
        ),
        default_maximum_order_fraction=(
            settings
            .trading_control_maximum_order_fraction
        ),
    )


@router.get(
    "/{account_id}",
    response_model=TradingControlResponse,
)
def get_trading_control(
    account_id: UUID,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = build_trading_control_service(
        session=session
    )

    try:
        control = service.ensure_for_account(
            account_id=account_id
        )

    except LookupError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    return TradingControlResponse.model_validate(
        control
    )


@router.post(
    "/{account_id}/halt",
    response_model=TradingControlResponse,
)
def halt_trading(
    account_id: UUID,
    request: TradingHaltRequest,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = build_trading_control_service(
        session=session
    )

    try:
        control = service.halt(
            account_id=account_id,
            reason=request.reason,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    return TradingControlResponse.model_validate(
        control
    )


@router.post(
    "/{account_id}/resume",
    response_model=TradingControlResponse,
)
def resume_trading(
    account_id: UUID,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = build_trading_control_service(
        session=session
    )

    try:
        control = service.resume(
            account_id=account_id
        )

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return TradingControlResponse.model_validate(
        control
    )


@router.post(
    "/{account_id}/reset-circuit-breaker",
    response_model=TradingControlResponse,
)
def reset_circuit_breaker(
    account_id: UUID,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = build_trading_control_service(
        session=session
    )

    try:
        control = (
            service.reset_circuit_breaker(
                account_id=account_id
            )
        )

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return TradingControlResponse.model_validate(
        control
    )


@router.post(
    "/{account_id}/enabled",
    response_model=TradingControlResponse,
)
def set_trading_enabled(
    account_id: UUID,
    request: TradingEnabledRequest,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = build_trading_control_service(
        session=session
    )

    try:
        control = service.set_enabled(
            account_id=account_id,
            enabled=request.enabled,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return TradingControlResponse.model_validate(
        control
    )