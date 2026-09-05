import pandas as pd
from sqlalchemy.orm import Session

from finai.infrastructure.backtesting.performance import (
    calculate_performance_metrics,
)
from finai.infrastructure.database.repositories.backtest_run_repository import (
    BacktestRunRepository,
)
from finai.infrastructure.database.repositories.portfolio_snapshot_repository import (
    PortfolioSnapshotRepository,
)


class RiskAnalysisService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._backtest_repository = BacktestRunRepository(session)

        self._snapshot_repository = PortfolioSnapshotRepository(session)

    def analyze(
        self,
        *,
        backtest_run_id,
    ) -> dict[str, float | None]:
        run = self._backtest_repository.get_by_id(backtest_run_id)

        if run is None:
            raise LookupError(f"Backtest not found: {backtest_run_id}")

        snapshots = self._snapshot_repository.list_for_backtest(backtest_run_id)

        if not snapshots:
            raise ValueError("Backtest does not contain portfolio snapshots.")

        equity_curve = pd.Series(
            [snapshot.equity for snapshot in snapshots],
            index=[snapshot.timestamp for snapshot in snapshots],
            dtype=float,
        )

        return calculate_performance_metrics(equity_curve)
