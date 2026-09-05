from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.order import (
    OrderResponse,
)
from finai.application.services.order_cancellation_service import (
    OrderCancellationService,
)
from finai.application.services.order_sync_service import (
    OrderSyncService,
)
from finai.core.config import (
    get_settings,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.execution.sandbox_broker import (
    SandboxBroker,
)


router = APIRouter(
    prefix="/api/v1/paper/execution",
    tags=["paper-execution"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_sandbox_broker() -> SandboxBroker:
    settings = get_settings()

    if settings.execution_mode != "sandbox":
        raise ValueError("Version 1.1 supports only sandbox execution.")

    return SandboxBroker(
        commission_bps=(settings.paper_trading_commission_bps),
        slippage_bps=(settings.paper_trading_slippage_bps),
        partial_fill_enabled=(settings.sandbox_partial_fill_enabled),
        initial_fill_fraction=(settings.sandbox_initial_fill_fraction),
    )


@router.post(
    "/orders/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order(
    order_id: UUID,
    session: DatabaseSession,
) -> OrderResponse:
    try:
        service = OrderCancellationService(
            session=session,
            broker=(build_sandbox_broker()),
        )

        order = service.cancel(order_id=order_id)

    except LookupError as error:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(error),
        ) from error

    return OrderResponse.model_validate(order)


@router.post(
    "/orders/{order_id}/sync",
    response_model=OrderResponse,
)
def sync_order(
    order_id: UUID,
    session: DatabaseSession,
) -> OrderResponse:
    settings = get_settings()

    try:
        service = OrderSyncService(
            session=session,
            commission_bps=(settings.paper_trading_commission_bps),
            slippage_bps=(settings.paper_trading_slippage_bps),
            maximum_quote_age_seconds=(settings.paper_quote_maximum_age_seconds),
            quote_interval=BarInterval(settings.paper_quote_interval),
            synthetic_spread_bps=(settings.paper_quote_synthetic_spread_bps),
        )

        order = service.sync(order_id=order_id)

    except LookupError as error:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(error),
        ) from error

    return OrderResponse.model_validate(order)
