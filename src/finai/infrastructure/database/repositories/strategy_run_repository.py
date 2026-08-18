from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.domain.strategy.run_enums import (
    StrategyRunStatus,
)
from finai.infrastructure.database.models.strategy_run import (
    StrategyRunModel,
)


class StrategyRunRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        idempotency_key: str,
        signal_count: int,
    ) -> StrategyRunModel:
        model = StrategyRunModel(
            account_id=account_id,
            strategy_key=strategy_key,
            idempotency_key=idempotency_key,
            status=(StrategyRunStatus.PENDING.value),
            signal_count=signal_count,
            proposal_count=0,
            rejected_count=0,
            failed_count=0,
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def get_by_id(
        self,
        run_id: UUID,
    ) -> StrategyRunModel | None:
        return self._session.get(
            StrategyRunModel,
            run_id,
        )

    def get_by_idempotency_key(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        idempotency_key: str,
    ) -> StrategyRunModel | None:
        statement = select(StrategyRunModel).where(
            StrategyRunModel.account_id == account_id,
            StrategyRunModel.strategy_key == strategy_key,
            StrategyRunModel.idempotency_key == idempotency_key,
        )

        return self._session.scalar(statement)

    def list_for_account(
        self,
        *,
        account_id: UUID,
        limit: int = 100,
    ) -> list[StrategyRunModel]:
        statement = (
            select(StrategyRunModel)
            .where(StrategyRunModel.account_id == account_id)
            .order_by(StrategyRunModel.created_at.desc())
            .limit(limit)
        )

        return list(self._session.scalars(statement).all())

    def mark_running(
        self,
        model: StrategyRunModel,
    ) -> StrategyRunModel:
        model.status = StrategyRunStatus.RUNNING.value

        model.started_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def complete(
        self,
        model: StrategyRunModel,
        *,
        proposal_count: int,
        rejected_count: int,
        failed_count: int,
    ) -> StrategyRunModel:
        model.proposal_count = proposal_count
        model.rejected_count = rejected_count
        model.failed_count = failed_count

        if failed_count == 0:
            model.status = StrategyRunStatus.COMPLETED.value

        elif proposal_count > 0 or rejected_count > 0:
            model.status = StrategyRunStatus.PARTIAL.value

        else:
            model.status = StrategyRunStatus.FAILED.value

        model.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_failed(
        self,
        model: StrategyRunModel,
        *,
        error_message: str,
    ) -> StrategyRunModel:
        model.status = StrategyRunStatus.FAILED.value

        model.error_message = error_message
        model.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model
