from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.backtest_run import (
    BacktestRunModel,
)


class BacktestRunRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        model_id: UUID,
        dataset_id: UUID,
        symbol: str,
        initial_capital: float,
        configuration: dict,
    ) -> BacktestRunModel:
        run = BacktestRunModel(
            model_id=model_id,
            dataset_id=dataset_id,
            symbol=symbol.strip().upper(),
            initial_capital=initial_capital,
            configuration=configuration,
            status="pending",
        )

        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)

        return run

    def get_by_id(
        self,
        run_id: UUID,
    ) -> BacktestRunModel | None:
        return self._session.get(
            BacktestRunModel,
            run_id,
        )

    def list_all(
        self,
    ) -> list[BacktestRunModel]:
        statement = select(BacktestRunModel).order_by(BacktestRunModel.created_at.desc())

        return list(self._session.scalars(statement))

    def mark_running(
        self,
        run: BacktestRunModel,
    ) -> BacktestRunModel:
        run.status = "running"
        run.started_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(run)

        return run

    def mark_completed(
        self,
        run: BacktestRunModel,
        *,
        final_equity: float,
        total_return: float,
        maximum_drawdown: float,
        sharpe_ratio: float | None,
        trade_count: int,
        metrics: dict,
    ) -> BacktestRunModel:
        run.status = "completed"
        run.final_equity = final_equity
        run.total_return = total_return
        run.maximum_drawdown = maximum_drawdown
        run.sharpe_ratio = sharpe_ratio
        run.trade_count = trade_count
        run.metrics = metrics
        run.completed_at = datetime.now(UTC)
        run.error_message = None

        self._session.commit()
        self._session.refresh(run)

        return run

    def mark_failed(
        self,
        run: BacktestRunModel,
        *,
        error_message: str,
    ) -> BacktestRunModel:
        run.status = "failed"
        run.error_message = error_message[:4000]
        run.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(run)

        return run
