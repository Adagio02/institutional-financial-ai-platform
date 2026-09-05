from __future__ import annotations

from dataclasses import asdict

from finai.application.services.v32_learning_service import (
    V32LearningCycleResult,
)


class V32MlflowService:
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
        result: V32LearningCycleResult,
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
                        "version": "3.2",
                        "symbol": result.symbol,
                        "interval": result.interval,
                        "winning_model": (
                            result.winning_model
                        ),
                        "rows_loaded": (
                            result.rows_loaded
                        ),
                        "rows_used": (
                            result.rows_used
                        ),
                        "research_rows": (
                            result.research_rows
                        ),
                        "holdout_rows": (
                            result.holdout_rows
                        ),
                    }
                )

                mlflow.log_metrics(
                    {
                        "walk_forward_balanced_accuracy": (
                            result
                            .walk_forward_balanced_accuracy
                        ),
                        "walk_forward_macro_f1": (
                            result
                            .walk_forward_macro_f1
                        ),
                        "walk_forward_net_return": (
                            result
                            .walk_forward_net_return
                        ),
                        "holdout_balanced_accuracy": (
                            result
                            .holdout_balanced_accuracy
                        ),
                        "holdout_macro_f1": (
                            result
                            .holdout_macro_f1
                        ),
                        "holdout_net_return": (
                            result
                            .holdout_net_return
                        ),
                        "holdout_maximum_drawdown": (
                            result
                            .holdout_maximum_drawdown
                        ),
                        "holdout_sharpe_like": (
                            result
                            .holdout_sharpe_like
                        ),
                        "holdout_trade_count": float(
                            result
                            .holdout_trade_count
                        ),
                        "candidate_composite_score": (
                            result
                            .candidate_composite_score
                        ),
                        "baseline_composite_score": (
                            result
                            .baseline_composite_score
                        ),
                        "promoted": float(
                            result.promoted
                        ),
                    }
                )

                mlflow.log_dict(
                    asdict(result),
                    "v32_learning_cycle.json",
                )

            return True

        except Exception:
            return False