from __future__ import annotations

from dataclasses import (
    asdict,
)
from pathlib import Path

from finai.application.services.adaptive_learning_service import (
    LearningCycleResult,
)


class V30MlflowService:
    def __init__(
        self,
        *,
        tracking_uri: str,
        experiment_name: str,
    ) -> None:
        self._tracking_uri = (
            tracking_uri.strip()
        )

        self._experiment_name = (
            experiment_name.strip()
        )

    def log_learning_cycle(
        self,
        *,
        result: LearningCycleResult,
    ) -> bool:
        try:
            import mlflow

        except ImportError:
            return False

        try:
            mlflow.set_tracking_uri(
                self._tracking_uri
            )

            mlflow.set_experiment(
                self._experiment_name
            )

            with mlflow.start_run():
                mlflow.log_params(
                    {
                        "symbol": result.symbol,
                        "interval": result.interval,
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
                        "candidate_accuracy": (
                            result
                            .candidate_accuracy
                        ),
                        "candidate_balanced_accuracy": (
                            result
                            .candidate_balanced_accuracy
                        ),
                        "candidate_log_loss": (
                            result
                            .candidate_log_loss
                        ),
                        "promoted": float(
                            result.promoted
                        ),
                    }
                )

                if (
                    result
                    .champion_balanced_accuracy
                    is not None
                ):
                    mlflow.log_metric(
                        "champion_balanced_accuracy",
                        result
                        .champion_balanced_accuracy,
                    )

                candidate_path = Path(
                    result.candidate_path
                )

                if candidate_path.exists():
                    mlflow.log_artifact(
                        str(candidate_path)
                    )

                mlflow.log_dict(
                    asdict(result),
                    "learning_cycle.json",
                )

            return True

        except Exception:
            return False