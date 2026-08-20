from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.strategy import (
    ProposalDecisionRequest,
    ProposalRejectionRequest,
    TradeProposalCreate,
    TradeProposalResponse,
)
from finai.application.services.proposal_approval_service import (
    ProposalApprovalService,
)
from finai.application.services.proposal_execution_service import (
    ProposalExecutionService,
)
from finai.application.services.strategy_proposal_service import (
    StrategyProposalService,
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
from finai.infrastructure.database.repositories.trade_proposal_repository import (
    TradeProposalRepository,
)


router = APIRouter(
    prefix="/api/v1/strategy/proposals",
    tags=["strategy"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_risk_limits() -> PortfolioRiskLimits:
    settings = get_settings()

    return PortfolioRiskLimits(
        maximum_order_notional=(settings.paper_maximum_order_notional),
        maximum_position_notional=(settings.paper_maximum_position_notional),
        maximum_gross_exposure=(settings.paper_maximum_gross_exposure),
        maximum_position_fraction=(settings.paper_maximum_position_fraction),
        minimum_cash_reserve_fraction=(settings.paper_minimum_cash_reserve_fraction),
    )


def build_strategy_proposal_service(
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
        # Note: default_* strategy settings provided above; duplicates removed
    )


def build_proposal_execution_service(
    *,
    session: Session,
) -> ProposalExecutionService:
    settings = get_settings()

    return ProposalExecutionService(
        session=session,
        commission_bps=(
            settings.paper_trading_commission_bps
        ),
        slippage_bps=(
            settings.paper_trading_slippage_bps
        ),
        risk_limits=(
            build_risk_limits()
        ),
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
        proposal_maximum_age_seconds=(
            settings.strategy_proposal_maximum_age_seconds
        ),
        maximum_price_drift_bps=(
            settings.strategy_maximum_price_drift_bps
        ),
        manual_approval_required=(
            settings.strategy_manual_approval_required
        ),
    )


@router.post(
    "",
    response_model=TradeProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trade_proposal(
    request: TradeProposalCreate,
    session: DatabaseSession,
) -> TradeProposalResponse:
    service = build_strategy_proposal_service(session=session)

    try:
        proposal = service.create(
            account_id=request.account_id,
            strategy_key=request.strategy_key,
            symbol=request.symbol,
            side=request.side,
            confidence=request.confidence,
            source_model_id=(request.source_model_id),
            source_prediction_id=(request.source_prediction_id),
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

    return TradeProposalResponse.model_validate(proposal)


@router.get(
    "/account/{account_id}",
    response_model=list[TradeProposalResponse],
)
def list_trade_proposals(
    account_id: UUID,
    session: DatabaseSession,
) -> list[TradeProposalResponse]:
    repository = TradeProposalRepository(session)

    return [
        TradeProposalResponse.model_validate(proposal)
        for proposal in repository.list_for_account(account_id)
    ]


@router.get(
    "/{proposal_id}",
    response_model=TradeProposalResponse,
)
def get_trade_proposal(
    proposal_id: UUID,
    session: DatabaseSession,
) -> TradeProposalResponse:
    repository = TradeProposalRepository(session)

    proposal = repository.get_by_id(proposal_id)

    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Trade proposal not found: {proposal_id}"),
        )

    return TradeProposalResponse.model_validate(proposal)


@router.post(
    "/{proposal_id}/approve",
    response_model=TradeProposalResponse,
)
def approve_trade_proposal(
    proposal_id: UUID,
    request: ProposalDecisionRequest,
    session: DatabaseSession,
) -> TradeProposalResponse:
    service = ProposalApprovalService(session=session)

    try:
        proposal = service.approve(
            proposal_id=proposal_id,
            reason=request.reason,
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

    return TradeProposalResponse.model_validate(proposal)


@router.post(
    "/{proposal_id}/reject",
    response_model=TradeProposalResponse,
)
def reject_trade_proposal(
    proposal_id: UUID,
    request: ProposalRejectionRequest,
    session: DatabaseSession,
) -> TradeProposalResponse:
    service = ProposalApprovalService(session=session)

    try:
        proposal = service.reject(
            proposal_id=proposal_id,
            reason=request.reason,
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

    return TradeProposalResponse.model_validate(proposal)


@router.post(
    "/{proposal_id}/execute",
    response_model=TradeProposalResponse,
)
def execute_trade_proposal(
    proposal_id: UUID,
    session: DatabaseSession,
) -> TradeProposalResponse:
    service = build_proposal_execution_service(session=session)

    try:
        proposal = service.execute(proposal_id=proposal_id)

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

    return TradeProposalResponse.model_validate(proposal)
