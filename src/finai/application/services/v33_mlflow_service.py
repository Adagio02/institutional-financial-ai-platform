from __future__ import annotations

from dataclasses import asdict

from finai.application.services.v33_learning_service import (
    V33LearningCycleResult,
)


class V33MlflowService:
    def __init__(
        self,
        *,
        tracking_uri: str,
        experiment_name: str,
    ) -> None:
        self._tracking_uri = (
            tracking_uri
        )

        self._experiment_name = (
            experiment_name
        )

    def log_learning_cycle(
        self,
        *,
        result: V33LearningCycleResult,
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
                        "version": "3.3",
                        "symbol": (
                            result.symbol
                        ),
                        "interval": (
                            result.interval
                        ),
                        "winning_model": (
                            result.winning_model
                        ),
                        "long_threshold": (
                            result
                            .selected_long_threshold
                        ),
                        "short_threshold": (
                            result
                            .selected_short_threshold
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
                        "purge_rows": (
                            result.purge_rows
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
                        "walk_forward_trade_count": float(
                            result
                            .walk_forward_trade_count
                        ),
                        "walk_forward_turnover": (
                            result
                            .walk_forward_turnover
                        ),
                        "walk_forward_maximum_drawdown": (
                            result
                            .walk_forward_maximum_drawdown
                        ),
                        "positive_fold_fraction": (
                            result
                            .positive_fold_fraction
                        ),
                        "holdout_balanced_accuracy": (
                            result
                            .holdout_balanced_accuracy
                        ),
                        "holdout_macro_f1": (
                            result
                            .holdout_macro_f1
                        ),
                        "holdout_gross_return": (
                            result
                            .holdout_gross_return
                        ),
                        "holdout_transaction_cost": (
                            result
                            .holdout_transaction_cost
                        ),
                        "holdout_net_return": (
                            result
                            .holdout_net_return
                        ),
                        "holdout_trade_count": float(
                            result
                            .holdout_trade_count
                        ),
                        "holdout_turnover": (
                            result
                            .holdout_turnover
                        ),
                        "holdout_maximum_drawdown": (
                            result
                            .holdout_maximum_drawdown
                        ),
                        "holdout_sharpe_like": (
                            result
                            .holdout_sharpe_like
                        ),
                        "baseline_net_return": (
                            result
                            .baseline_net_return
                        ),
                        "candidate_composite_score": (
                            result
                            .candidate_composite_score
                        ),
                        "promoted": float(
                            result.promoted
                        ),
                    }
                )

                mlflow.log_dict(
                    asdict(
                        result
                    ),
                    "v33_learning_cycle.json",
                )

            return True

        except Exception as error:
            print(
                "MLflow logging failed:",
                repr(
                    error
                ),
            )

            return False