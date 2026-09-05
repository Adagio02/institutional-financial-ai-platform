from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.backtest import (
    BacktestCreate,
    BacktestResponse,
    PortfolioSnapshotResponse,
    SimulatedTradeResponse,
)
from finai.application.services.backtest_service import (
    BacktestService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.backtest_run_repository import (
    BacktestRunRepository,
)
from finai.infrastructure.database.repositories.portfolio_snapshot_repository import (
    PortfolioSnapshotRepository,
)
from finai.infrastructure.database.repositories.simulated_trade_repository import (
    SimulatedTradeRepository,
)


router = APIRouter(
    prefix="/api/v1/backtests",
    tags=["backtests"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "",
    response_model=BacktestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_backtest(
    request: BacktestCreate,
    session: DatabaseSession,
) -> BacktestResponse:
    service = BacktestService(
        session=session,
    )

    try:
        run = service.run(
            model_id=request.model_id,
            dataset_id=request.dataset_id,
            symbol=request.symbol,
            initial_capital=request.initial_capital,
            long_threshold=request.long_threshold,
            short_threshold=request.short_threshold,
            position_size_fraction=request.position_size_fraction,
            commission_bps=request.commission_bps,
            slippage_bps=request.slippage_bps,
            allow_short=request.allow_short,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except (
        ValueError,
        FileNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return BacktestResponse.model_validate(run)


@router.get(
    "",
    response_model=list[BacktestResponse],
)
def list_backtests(
    session: DatabaseSession,
) -> list[BacktestResponse]:
    repository = BacktestRunRepository(session)

    return [BacktestResponse.model_validate(run) for run in repository.list_all()]


@router.get(
    "/{backtest_run_id}",
    response_model=BacktestResponse,
)
def get_backtest(
    backtest_run_id: UUID,
    session: DatabaseSession,
) -> BacktestResponse:
    repository = BacktestRunRepository(session)

    run = repository.get_by_id(backtest_run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Backtest not found: {backtest_run_id}"),
        )

    return BacktestResponse.model_validate(run)


@router.get(
    "/{backtest_run_id}/trades",
    response_model=list[SimulatedTradeResponse],
)
def list_backtest_trades(
    backtest_run_id: UUID,
    session: DatabaseSession,
) -> list[SimulatedTradeResponse]:
    repository = SimulatedTradeRepository(session)

    return [
        SimulatedTradeResponse.model_validate(trade)
        for trade in repository.list_for_backtest(backtest_run_id)
    ]


@router.get(
    "/{backtest_run_id}/equity",
    response_model=list[PortfolioSnapshotResponse],
)
def list_equity_curve(
    backtest_run_id: UUID,
    session: DatabaseSession,
) -> list[PortfolioSnapshotResponse]:
    repository = PortfolioSnapshotRepository(session)

    return [
        PortfolioSnapshotResponse.model_validate(snapshot)
        for snapshot in repository.list_for_backtest(backtest_run_id)
    ]
