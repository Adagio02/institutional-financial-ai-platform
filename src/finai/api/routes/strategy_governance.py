from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.strategy_governance import (
    StrategyPerformanceResponse,
    StrategyPolicyResponse,
    StrategyPolicyUpdate,
)
from finai.application.services.strategy_governance_service import (
    StrategyGovernanceService,
)
from finai.core.config import (
    get_settings,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.strategy_attribution_repository import (
    StrategyAttributionRepository,
)
from finai.infrastructure.database.repositories.strategy_policy_repository import (
    StrategyPolicyRepository,
)
from finai.infrastructure.database.repositories.strategy_position_repository import (
    StrategyPositionRepository,
)


router = APIRouter(
    prefix="/api/v1/strategy/governance",
    tags=["strategy-governance"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_service(
    *,
    session: Session,
) -> StrategyGovernanceService:
    settings = get_settings()

    return StrategyGovernanceService(
        session=session,
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


@router.get(
    "/policies/{account_id}/{strategy_key}",
    response_model=StrategyPolicyResponse,
)
def get_strategy_policy(
    account_id: UUID,
    strategy_key: str,
    session: DatabaseSession,
) -> StrategyPolicyResponse:
    account_repository = PaperAccountRepository(session)

    if account_repository.get_by_id(account_id) is None:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=(f"Paper account not found: {account_id}"),
        )

    service = build_service(session=session)

    policy = service.get_or_create_policy(
        account_id=account_id,
        strategy_key=strategy_key,
    )

    return StrategyPolicyResponse.model_validate(policy)


@router.put(
    "/policies/{account_id}/{strategy_key}",
    response_model=StrategyPolicyResponse,
)
def update_strategy_policy(
    account_id: UUID,
    strategy_key: str,
    request: StrategyPolicyUpdate,
    session: DatabaseSession,
) -> StrategyPolicyResponse:
    service = build_service(session=session)

    policy = service.get_or_create_policy(
        account_id=account_id,
        strategy_key=strategy_key,
    )

    policy.enabled = request.enabled

    policy.allow_buy = request.allow_buy

    policy.allow_sell = request.allow_sell

    policy.capital_budget_fraction = request.capital_budget_fraction

    policy.maximum_single_proposal_fraction = request.maximum_single_proposal_fraction

    policy.maximum_gross_exposure_fraction = request.maximum_gross_exposure_fraction

    policy.maximum_symbol_fraction = request.maximum_symbol_fraction

    policy.maximum_daily_loss = request.maximum_daily_loss

    policy.cooldown_seconds = request.cooldown_seconds

    policy.maximum_active_proposals = request.maximum_active_proposals

    repository = StrategyPolicyRepository(session)

    saved = repository.save(policy)

    return StrategyPolicyResponse.model_validate(saved)


@router.get(
    "/performance/{account_id}/{strategy_key}",
    response_model=(StrategyPerformanceResponse),
)
def get_strategy_performance(
    account_id: UUID,
    strategy_key: str,
    session: DatabaseSession,
) -> StrategyPerformanceResponse:
    attribution_repository = StrategyAttributionRepository(session)

    position_repository = StrategyPositionRepository(session)

    positions = position_repository.list_for_strategy(
        account_id=account_id,
        strategy_key=strategy_key,
    )

    gross_exposure = sum(abs(position.quantity * position.average_price) for position in positions)

    daily_pnl = attribution_repository.daily_net_pnl(
        account_id=account_id,
        strategy_key=strategy_key,
    )

    return StrategyPerformanceResponse(
        account_id=account_id,
        strategy_key=strategy_key,
        daily_net_pnl=daily_pnl,
        gross_book_exposure=(gross_exposure),
        position_count=len(positions),
    )
