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

from finai.api.schemas.strategy_run import (
    StrategyRunCreate,
    StrategyRunDetailResponse,
    StrategyRunItemResponse,
    StrategyRunResponse,
)
from finai.application.services.strategy_proposal_service import (
    StrategyProposalService,
)
from finai.application.services.strategy_run_service import (
    StrategyRunService,
    StrategySignal,
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
from finai.infrastructure.database.repositories.strategy_run_repository import (
    StrategyRunRepository,
)


router = APIRouter(
    prefix="/api/v1/strategy/runs",
    tags=["strategy-runs"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_proposal_service(
    *,
    session: Session,
) -> StrategyProposalService:
    settings = get_settings()

    return StrategyProposalService(
        session=session,
        minimum_confidence=(settings.strategy_minimum_confidence),
        maximum_buy_equity_fraction=(settings.strategy_maximum_buy_equity_fraction),
        maximum_sell_position_fraction=(settings.strategy_maximum_sell_position_fraction),
        minimum_order_notional=(settings.strategy_minimum_order_notional),
        maximum_quote_age_seconds=(settings.paper_quote_maximum_age_seconds),
        quote_interval=BarInterval(settings.paper_quote_interval),
        synthetic_spread_bps=(settings.paper_quote_synthetic_spread_bps),
        default_capital_budget_fraction=(settings.strategy_default_capital_budget_fraction),
        default_maximum_single_proposal_fraction=(
            settings.strategy_default_maximum_single_proposal_fraction
        ),
        default_maximum_gross_exposure_fraction=(
            settings.strategy_default_maximum_gross_exposure_fraction
        ),
        default_maximum_symbol_fraction=(settings.strategy_default_maximum_symbol_fraction),
        default_maximum_daily_loss=(settings.strategy_default_maximum_daily_loss),
        default_cooldown_seconds=(settings.strategy_default_cooldown_seconds),
        default_maximum_active_proposals=(settings.strategy_default_maximum_active_proposals),
        competing_signal_resolution_enabled=(settings.strategy_competing_signal_resolution_enabled),
    )


def build_run_service(
    *,
    session: Session,
) -> StrategyRunService:
    settings = get_settings()

    return StrategyRunService(
        session=session,
        proposal_service=(build_proposal_service(session=session)),
        maximum_signals_per_run=(settings.strategy_run_maximum_signals),
    )


def build_detail_response(
    *,
    service: StrategyRunService,
    run,
) -> StrategyRunDetailResponse:
    items = service.list_items(run_id=run.id)

    base = StrategyRunResponse.model_validate(run)

    return StrategyRunDetailResponse(
        **base.model_dump(),
        items=[StrategyRunItemResponse.model_validate(item) for item in items],
    )


@router.post(
    "",
    response_model=(StrategyRunDetailResponse),
    status_code=(status.HTTP_201_CREATED),
)
def create_strategy_run(
    request: StrategyRunCreate,
    session: DatabaseSession,
) -> StrategyRunDetailResponse:
    service = build_run_service(session=session)

    signals = [
        StrategySignal(
            symbol=signal.symbol,
            side=signal.side,
            confidence=signal.confidence,
            source_model_id=(signal.source_model_id),
            source_prediction_id=(signal.source_prediction_id),
        )
        for signal in request.signals
    ]

    try:
        run = service.execute(
            account_id=request.account_id,
            strategy_key=(request.strategy_key),
            idempotency_key=(request.idempotency_key),
            signals=signals,
        )

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

    return build_detail_response(
        service=service,
        run=run,
    )


@router.get(
    "/{run_id}",
    response_model=(StrategyRunDetailResponse),
)
def get_strategy_run(
    run_id: UUID,
    session: DatabaseSession,
) -> StrategyRunDetailResponse:
    service = build_run_service(session=session)

    try:
        run = service.get(run_id=run_id)

    except LookupError as error:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(error),
        ) from error

    return build_detail_response(
        service=service,
        run=run,
    )


@router.get(
    "/account/{account_id}",
    response_model=list[StrategyRunResponse],
)
def list_strategy_runs(
    account_id: UUID,
    session: DatabaseSession,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
        ),
    ] = 100,
) -> list[StrategyRunResponse]:
    repository = StrategyRunRepository(session)

    runs = repository.list_for_account(
        account_id=account_id,
        limit=limit,
    )

    return [StrategyRunResponse.model_validate(run) for run in runs]
