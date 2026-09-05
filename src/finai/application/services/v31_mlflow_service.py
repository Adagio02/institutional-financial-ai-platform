from __future__ import annotations

from dataclasses import asdict

from finai.application.services.v31_learning_service import (
    V31LearningCycleResult,
)


class V31MlflowService:
    def __init__(
        self,
        *,
        tracking_uri: str,
        experiment_name: str,
    ) -> None:
        self._tracking_uri = tracking_uri
        self._experiment_name = (
            experiment_name
        )

    def log_learning_cycle(
        self,
        *,
        result: V31LearningCycleResult,
    ) -> bool:
        try:
            import mlflow

            mlflow.set_tracking_uri(
                self._tracking_uri
            )

            mlflow.set_experiment(
                self._experiment_name
            )

            with mlflow.start_run():
                mlflow.log_params(
                    {
                        "version": "3.1",
                        "symbol": (
                            result.symbol
                        ),
                        "interval": (
                            result.interval
                        ),
                        "winning_model": (
                            result.winning_model
                        ),
                        "rows_loaded": (
                            result.rows_loaded
                        ),
                        "rows_used": (
                            result.rows_used
                        ),
                    }
                )

                mlflow.log_metrics(
                    {
                        "balanced_accuracy": (
                            result
                            .balanced_accuracy
                        ),
                        "macro_f1": (
                            result
                            .macro_f1
                        ),
                        "gross_return": (
                            result
                            .gross_return
                        ),
                        "transaction_cost": (
                            result
                            .transaction_cost
                        ),
                        "net_return": (
                            result
                            .net_return
                        ),
                        "trade_count": float(
                            result.trade_count
                        ),
                        "composite_score": (
                            result
                            .composite_score
                        ),
                        "promoted": float(
                            result.promoted
                        ),
                    }
                )

                mlflow.log_dict(
                    asdict(result),
                    "v31_learning_cycle.json",
                )

            return True

        except Exception:
            return False