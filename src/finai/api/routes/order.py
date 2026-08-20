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
    FillResponse,
    OrderCreate,
    OrderResponse,
)
from finai.application.services.order_cancellation_service import (
    OrderCancellationService,
)
from finai.application.services.order_service import (
    OrderService,
)
from finai.core.config import (
    get_settings,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.execution_fill_repository import (
    ExecutionFillRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)


router = APIRouter(
    prefix="/api/v1/paper/orders",
    tags=["paper-trading"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_order_service(
    *,
    session: Session,
) -> OrderService:
    settings = get_settings()

    risk_limits = PortfolioRiskLimits(
        maximum_order_notional=(
            settings.paper_maximum_order_notional
        ),
        maximum_position_notional=(
            settings.paper_maximum_position_notional
        ),
        maximum_gross_exposure=(
            settings.paper_maximum_gross_exposure
        ),
        maximum_position_fraction=(
            settings.paper_maximum_position_fraction
        ),
        minimum_cash_reserve_fraction=(
            settings.paper_minimum_cash_reserve_fraction
        ),
    )

    return OrderService(
        session=session,
        commission_bps=(
            settings.paper_trading_commission_bps
        ),
        slippage_bps=(
            settings.paper_trading_slippage_bps
        ),
        risk_limits=risk_limits,
        maximum_quote_age_seconds=(
            settings.paper_quote_maximum_age_seconds
        ),
        quote_interval=BarInterval(
            settings.paper_quote_interval
        ),
        synthetic_spread_bps=(
            settings.paper_quote_synthetic_spread_bps
        ),
        trading_control_maximum_daily_loss_fraction=(
            settings.trading_control_maximum_daily_loss_fraction
        ),
        trading_control_maximum_gross_exposure_fraction=(
            settings.trading_control_maximum_gross_exposure_fraction
        ),
        trading_control_maximum_symbol_fraction=(
            settings.trading_control_maximum_symbol_fraction
        ),
        trading_control_maximum_order_fraction=(
            settings.trading_control_maximum_order_fraction
        ),
        partial_fill_enabled=(
            settings.sandbox_partial_fill_enabled
        ),
        initial_fill_fraction=(
            settings.sandbox_initial_fill_fraction
        ),
        execution_mode=(
            settings.execution_mode
        ),
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_order(
    request: OrderCreate,
    session: DatabaseSession,
) -> OrderResponse:
    service = build_order_service(
        session=session
    )

    try:
        order = service.submit(
            account_id=request.account_id,
            client_order_id=(
                request.client_order_id
            ),
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            limit_price=request.limit_price,
            time_in_force=(
                request.time_in_force
            ),
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

    return OrderResponse.model_validate(
        order
    )


@router.get(
    "/account/{account_id}",
    response_model=list[OrderResponse],
)
def list_orders(
    account_id: UUID,
    session: DatabaseSession,
) -> list[OrderResponse]:
    repository = OrderRepository(
        session
    )

    return [
        OrderResponse.model_validate(
            order
        )
        for order
        in repository.list_for_account(
            account_id
        )
    ]


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: UUID,
    session: DatabaseSession,
) -> OrderResponse:
    repository = OrderRepository(
        session
    )

    order = repository.get_by_id(
        order_id
    )

    if order is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                f"Order not found: {order_id}"
            ),
        )

    return OrderResponse.model_validate(
        order
    )


@router.get(
    "/{order_id}/fills",
    response_model=list[FillResponse],
)
def list_order_fills(
    order_id: UUID,
    session: DatabaseSession,
) -> list[FillResponse]:
    repository = (
        ExecutionFillRepository(
            session
        )
    )

    return [
        FillResponse.model_validate(
            fill
        )
        for fill
        in repository.list_for_order(
            order_id
        )
    ]


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
)
def cancel_order(
    order_id: UUID,
    session: DatabaseSession,
) -> OrderResponse:
    service = (
        OrderCancellationService(
            session=session
        )
    )

    try:
        order = service.cancel(
            order_id=order_id
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

    return OrderResponse.model_validate(
        order
    )