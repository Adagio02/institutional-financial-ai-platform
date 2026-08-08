from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.risk import (
    BacktestRiskResponse,
)
from finai.application.services.risk_analysis_service import (
    RiskAnalysisService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)


router = APIRouter(
    prefix="/api/v1/risk",
    tags=["risk"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.get(
    "/backtests/{backtest_run_id}",
    response_model=BacktestRiskResponse,
)
def get_backtest_risk(
    backtest_run_id: UUID,
    session: DatabaseSession,
) -> BacktestRiskResponse:
    service = RiskAnalysisService(session=session)

    try:
        metrics = service.analyze(backtest_run_id=(backtest_run_id))

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

    return BacktestRiskResponse(
        backtest_run_id=backtest_run_id,
        **metrics,
    )
