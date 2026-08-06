from contextlib import contextmanager
from typing import Any, Iterator

import mlflow


class MLflowTrackingClient:
    def __init__(
        self,
        *,
        tracking_uri: str,
        experiment_name: str,
    ) -> None:
        mlflow.set_tracking_uri(tracking_uri)

        mlflow.set_experiment(experiment_name)

    @contextmanager
    def start_run(
        self,
        *,
        run_name: str,
    ) -> Iterator[str]:
        with mlflow.start_run(run_name=run_name) as active_run:
            yield active_run.info.run_id

    @staticmethod
    def log_parameters(
        parameters: dict[str, Any],
    ) -> None:
        safe_parameters = {key: str(value) for key, value in parameters.items()}

        mlflow.log_params(safe_parameters)

    @staticmethod
    def log_metrics(
        metrics: dict[str, float],
    ) -> None:
        mlflow.log_metrics(metrics)

    @staticmethod
    def log_artifact(
        artifact_path: str,
    ) -> None:
        mlflow.log_artifact(artifact_path)
