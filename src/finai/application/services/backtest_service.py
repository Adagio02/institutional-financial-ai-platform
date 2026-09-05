from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from finai.domain.backtesting.enums import (
    SignalDirection,
    TradeSide,
)
from finai.domain.backtesting.validation import (
    validate_backtest_configuration,
)
from finai.infrastructure.backtesting.execution_simulator import (
    apply_slippage,
    calculate_transaction_cost,
)
from finai.infrastructure.backtesting.performance import (
    calculate_performance_metrics,
)
from finai.infrastructure.backtesting.position_sizer import (
    calculate_position_notional,
    calculate_quantity,
)
from finai.infrastructure.backtesting.signal_generator import (
    generate_classification_signal,
    generate_regression_signal,
)
from finai.infrastructure.database.repositories.backtest_run_repository import (
    BacktestRunRepository,
)
from finai.infrastructure.database.repositories.dataset_version_repository import (
    DatasetVersionRepository,
)
from finai.infrastructure.database.repositories.model_artifact_repository import (
    ModelArtifactRepository,
)
from finai.infrastructure.database.repositories.portfolio_snapshot_repository import (
    PortfolioSnapshotRepository,
)
from finai.infrastructure.database.repositories.simulated_trade_repository import (
    SimulatedTradeRepository,
)
from finai.infrastructure.database.repositories.training_run_repository import (
    TrainingRunRepository,
)
from finai.infrastructure.prediction.model_loader import (
    ModelLoader,
)


class BacktestService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._dataset_repository = DatasetVersionRepository(session)

        self._model_repository = ModelArtifactRepository(session)

        self._training_repository = TrainingRunRepository(session)

        self._backtest_repository = BacktestRunRepository(session)

        self._trade_repository = SimulatedTradeRepository(session)

        self._snapshot_repository = PortfolioSnapshotRepository(session)

        self._model_loader = ModelLoader()

    def run(
        self,
        *,
        model_id: UUID,
        dataset_id: UUID,
        symbol: str,
        initial_capital: float,
        long_threshold: float,
        short_threshold: float,
        position_size_fraction: float,
        commission_bps: float,
        slippage_bps: float,
        allow_short: bool,
    ):
        validate_backtest_configuration(
            initial_capital=initial_capital,
            long_threshold=long_threshold,
            short_threshold=short_threshold,
            position_size_fraction=(position_size_fraction),
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )

        model_artifact = self._model_repository.get_by_id(model_id)

        if model_artifact is None:
            raise LookupError(f"Model not found: {model_id}")

        dataset = self._dataset_repository.get_by_id(dataset_id)

        if dataset is None:
            raise LookupError(f"Dataset not found: {dataset_id}")

        if dataset.status != "completed":
            raise ValueError("Backtesting requires a completed dataset.")

        if not dataset.storage_uri:
            raise ValueError("Dataset does not have a storage URI.")

        expected_dataset_id = model_artifact.metadata_json.get("dataset_id")

        if expected_dataset_id and expected_dataset_id != str(dataset.id):
            raise ValueError("Dataset does not match model lineage.")

        training_run = self._training_repository.get_by_id(model_artifact.training_run_id)

        if training_run is None:
            raise LookupError("Training run was not found.")

        configuration = {
            "long_threshold": long_threshold,
            "short_threshold": short_threshold,
            "position_size_fraction": (position_size_fraction),
            "commission_bps": commission_bps,
            "slippage_bps": slippage_bps,
            "allow_short": allow_short,
        }

        run = self._backtest_repository.create(
            model_id=model_id,
            dataset_id=dataset_id,
            symbol=symbol,
            initial_capital=initial_capital,
            configuration=configuration,
        )

        self._backtest_repository.mark_running(run)

        try:
            frame = pd.read_parquet(Path(dataset.storage_uri)).sort_index()

            feature_columns = list(model_artifact.feature_columns)

            frame = frame.dropna(subset=feature_columns)

            if frame.empty:
                raise ValueError("No complete feature rows are available for backtesting.")

            model = self._model_loader.load(
                artifact_uri=(model_artifact.artifact_uri),
                artifact_hash=(model_artifact.artifact_hash),
            )

            predictions = model.predict(frame[feature_columns])

            probabilities = None

            if hasattr(
                model,
                "predict_proba",
            ):
                probabilities = model.predict_proba(frame[feature_columns])[:, 1]

            price_column = self._resolve_price_column(frame)

            trades, snapshots = self._simulate(
                run_id=run.id,
                frame=frame,
                predictions=np.asarray(predictions),
                probabilities=probabilities,
                prediction_task=(training_run.prediction_task),
                price_column=price_column,
                initial_capital=initial_capital,
                long_threshold=(long_threshold),
                short_threshold=(short_threshold),
                position_size_fraction=(position_size_fraction),
                commission_bps=(commission_bps),
                slippage_bps=(slippage_bps),
                allow_short=allow_short,
            )

            self._trade_repository.create_many(trades=trades)

            self._snapshot_repository.create_many(snapshots=snapshots)

            equity_curve = pd.Series(
                [snapshot["equity"] for snapshot in snapshots],
                index=[snapshot["timestamp"] for snapshot in snapshots],
                dtype=float,
            )

            metrics = calculate_performance_metrics(equity_curve)

            return self._backtest_repository.mark_completed(
                run,
                final_equity=float(metrics["final_equity"]),
                total_return=float(metrics["total_return"]),
                maximum_drawdown=float(metrics["maximum_drawdown"]),
                sharpe_ratio=(metrics["sharpe_ratio"]),
                trade_count=len(trades),
                metrics=metrics,
            )

        except Exception as error:
            self._backtest_repository.mark_failed(
                run,
                error_message=str(error),
            )

            raise

    @staticmethod
    def _resolve_price_column(
        frame: pd.DataFrame,
    ) -> str:
        candidates = (
            "close",
            "close_price",
        )

        for candidate in candidates:
            if candidate in frame.columns:
                return candidate

        raise ValueError("Dataset requires a close or close_price column for backtesting.")

    @staticmethod
    def _simulate(
        *,
        run_id: UUID,
        frame: pd.DataFrame,
        predictions: np.ndarray,
        probabilities: np.ndarray | None,
        prediction_task: str,
        price_column: str,
        initial_capital: float,
        long_threshold: float,
        short_threshold: float,
        position_size_fraction: float,
        commission_bps: float,
        slippage_bps: float,
        allow_short: bool,
    ) -> tuple[list[dict], list[dict]]:
        cash = initial_capital
        position_quantity = 0.0
        peak_equity = initial_capital

        trades: list[dict] = []
        snapshots: list[dict] = []

        previous_signal = SignalDirection.FLAT

        for index, (
            timestamp,
            row,
        ) in enumerate(frame.iterrows()):
            market_price = float(row[price_column])

            if prediction_task == "classification":
                if probabilities is None:
                    probability = float(predictions[index])
                else:
                    probability = float(probabilities[index])

                signal = generate_classification_signal(
                    probability=probability,
                    long_threshold=(long_threshold),
                    short_threshold=(short_threshold),
                    allow_short=allow_short,
                )

            elif prediction_task == "regression":
                signal = generate_regression_signal(
                    prediction=float(predictions[index]),
                    long_threshold=(long_threshold),
                    short_threshold=(short_threshold),
                    allow_short=allow_short,
                )

            else:
                raise ValueError("Unsupported prediction task.")

            if signal != previous_signal:
                if position_quantity != 0:
                    closing_side = TradeSide.SELL if position_quantity > 0 else TradeSide.BUY

                    closing_price = apply_slippage(
                        price=market_price,
                        side=closing_side,
                        slippage_bps=(slippage_bps),
                    )

                    closing_notional = abs(position_quantity) * closing_price

                    cost = calculate_transaction_cost(
                        notional=(closing_notional),
                        commission_bps=(commission_bps),
                    )

                    cash += position_quantity * closing_price

                    cash -= cost

                    trades.append(
                        {
                            "backtest_run_id": (run_id),
                            "timestamp": (timestamp),
                            "side": (closing_side.value),
                            "quantity": abs(position_quantity),
                            "execution_price": (closing_price),
                            "notional": (closing_notional),
                            "transaction_cost": (cost),
                            "realized_pnl": 0.0,
                        }
                    )

                    position_quantity = 0.0

                if signal != SignalDirection.FLAT:
                    equity = cash

                    position_notional = calculate_position_notional(
                        portfolio_equity=(equity),
                        position_size_fraction=(position_size_fraction),
                    )

                    side = TradeSide.BUY if signal == SignalDirection.LONG else TradeSide.SELL

                    execution_price = apply_slippage(
                        price=market_price,
                        side=side,
                        slippage_bps=(slippage_bps),
                    )

                    quantity = calculate_quantity(
                        position_notional=(position_notional),
                        price=execution_price,
                    )

                    cost = calculate_transaction_cost(
                        notional=(position_notional),
                        commission_bps=(commission_bps),
                    )

                    if signal == SignalDirection.LONG:
                        cash -= quantity * execution_price
                        cash -= cost
                        position_quantity = quantity
                    else:
                        cash += quantity * execution_price
                        cash -= cost
                        position_quantity = -quantity

                    trades.append(
                        {
                            "backtest_run_id": run_id,
                            "timestamp": timestamp,
                            "side": side.value,
                            "quantity": quantity,
                            "execution_price": (execution_price),
                            "notional": (position_notional),
                            "transaction_cost": cost,
                            "realized_pnl": 0.0,
                        }
                    )

            market_value = position_quantity * market_price

            equity = cash + market_value

            peak_equity = max(
                peak_equity,
                equity,
            )

            drawdown = (equity / peak_equity) - 1.0

            snapshots.append(
                {
                    "backtest_run_id": run_id,
                    "timestamp": timestamp,
                    "cash": cash,
                    "position_quantity": (position_quantity),
                    "market_price": market_price,
                    "market_value": (market_value),
                    "equity": equity,
                    "drawdown": drawdown,
                }
            )

            previous_signal = signal

        return trades, snapshots
