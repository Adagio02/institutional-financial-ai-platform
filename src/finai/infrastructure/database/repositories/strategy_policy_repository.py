from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.strategy_policy import (
    StrategyPolicyModel,
)


class StrategyPolicyRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
    ) -> StrategyPolicyModel | None:
        statement = select(StrategyPolicyModel).where(
            StrategyPolicyModel.account_id == account_id,
            StrategyPolicyModel.strategy_key == strategy_key,
        )

        return self._session.scalar(statement)

    def create(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        enabled: bool,
        allow_buy: bool,
        allow_sell: bool,
        capital_budget_fraction: float,
        maximum_single_proposal_fraction: float,
        maximum_gross_exposure_fraction: float,
        maximum_symbol_fraction: float,
        maximum_daily_loss: float,
        cooldown_seconds: int,
        maximum_active_proposals: int,
    ) -> StrategyPolicyModel:
        model = StrategyPolicyModel(
            account_id=account_id,
            strategy_key=strategy_key,
            enabled=enabled,
            allow_buy=allow_buy,
            allow_sell=allow_sell,
            capital_budget_fraction=(capital_budget_fraction),
            maximum_single_proposal_fraction=(maximum_single_proposal_fraction),
            maximum_gross_exposure_fraction=(maximum_gross_exposure_fraction),
            maximum_symbol_fraction=(maximum_symbol_fraction),
            maximum_daily_loss=(maximum_daily_loss),
            cooldown_seconds=(cooldown_seconds),
            maximum_active_proposals=(maximum_active_proposals),
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def save(
        self,
        policy: StrategyPolicyModel,
    ) -> StrategyPolicyModel:
        self._session.add(policy)
        self._session.commit()
        self._session.refresh(policy)

        return policy
