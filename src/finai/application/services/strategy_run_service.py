from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.strategy_proposal_service import (
    StrategyProposalService,
)
from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.strategy.enums import (
    TradeProposalStatus,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.strategy_run_item_repository import (
    StrategyRunItemRepository,
)
from finai.infrastructure.database.repositories.strategy_run_repository import (
    StrategyRunRepository,
)


@dataclass(
    frozen=True,
    slots=True,
)
class StrategySignal:
    symbol: str
    side: OrderSide
    confidence: float
    source_model_id: UUID | None = None
    source_prediction_id: UUID | None = None


class StrategyRunService:
    def __init__(
        self,
        *,
        session: Session,
        proposal_service: StrategyProposalService,
        maximum_signals_per_run: int,
    ) -> None:
        self._account_repository = PaperAccountRepository(session)

        self._run_repository = StrategyRunRepository(session)

        self._item_repository = StrategyRunItemRepository(session)

        self._proposal_service = proposal_service

        self._maximum_signals_per_run = maximum_signals_per_run

    def execute(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        idempotency_key: str,
        signals: list[StrategySignal],
    ):
        normalized_strategy_key = strategy_key.strip()

        normalized_idempotency_key = idempotency_key.strip()

        if not normalized_strategy_key:
            raise ValueError("strategy_key cannot be blank.")

        if not normalized_idempotency_key:
            raise ValueError("idempotency_key cannot be blank.")

        if not signals:
            raise ValueError("Strategy run requires at least one signal.")

        if len(signals) > self._maximum_signals_per_run:
            raise ValueError("Strategy run exceeds the maximum signal count.")

        account = self._account_repository.get_by_id(account_id)

        if account is None:
            raise LookupError(f"Paper account not found: {account_id}")

        existing = self._run_repository.get_by_idempotency_key(
            account_id=account_id,
            strategy_key=(normalized_strategy_key),
            idempotency_key=(normalized_idempotency_key),
        )

        if existing is not None:
            return existing

        run = self._run_repository.create(
            account_id=account_id,
            strategy_key=(normalized_strategy_key),
            idempotency_key=(normalized_idempotency_key),
            signal_count=len(signals),
        )

        self._run_repository.mark_running(run)

        proposal_count = 0
        rejected_count = 0
        failed_count = 0

        for sequence_number, signal in enumerate(
            signals,
            start=1,
        ):
            item = self._item_repository.create(
                strategy_run_id=run.id,
                sequence_number=(sequence_number),
                symbol=signal.symbol,
                side=signal.side.value,
                confidence=(signal.confidence),
                source_model_id=(signal.source_model_id),
                source_prediction_id=(signal.source_prediction_id),
            )

            try:
                proposal = self._proposal_service.create(
                    account_id=account_id,
                    strategy_key=(normalized_strategy_key),
                    symbol=signal.symbol,
                    side=signal.side,
                    confidence=(signal.confidence),
                    source_model_id=(signal.source_model_id),
                    source_prediction_id=(signal.source_prediction_id),
                )

            except (
                LookupError,
                ValueError,
            ) as error:
                failed_count += 1

                self._item_repository.mark_failed(
                    item,
                    error_message=str(error),
                )

                continue

            self._item_repository.mark_proposal_created(
                item,
                proposal_id=(proposal.id),
            )

            proposal_count += 1

            if proposal.status == (TradeProposalStatus.REJECTED.value):
                rejected_count += 1

        return self._run_repository.complete(
            run,
            proposal_count=proposal_count,
            rejected_count=rejected_count,
            failed_count=failed_count,
        )

    def get(
        self,
        *,
        run_id: UUID,
    ):
        run = self._run_repository.get_by_id(run_id)

        if run is None:
            raise LookupError(f"Strategy run not found: {run_id}")

        return run

    def list_items(
        self,
        *,
        run_id: UUID,
    ):
        return self._item_repository.list_for_run(strategy_run_id=run_id)
