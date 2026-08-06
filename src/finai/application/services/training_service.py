import hashlib
from pathlib import Path
from uuid import UUID

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from finai.application.services.evaluation_service import (
    EvaluationService,
)
from finai.domain.modeling.enums import (
    ModelType,
    PredictionTask,
)
from finai.domain.modeling.validation import (
    validate_training_frame,
)
from finai.infrastructure.database.repositories.dataset_version_repository import (
    DatasetVersionRepository,
)
from finai.infrastructure.database.repositories.evaluation_result_repository import (
    EvaluationResultRepository,
)
from finai.infrastructure.database.repositories.model_artifact_repository import (
    ModelArtifactRepository,
)
from finai.infrastructure.database.repositories.training_run_repository import (
    TrainingRunRepository,
)
from finai.infrastructure.modeling.mlflow_client import (
    MLflowTrackingClient,
)
from finai.infrastructure.modeling.splitters.walk_forward_splitter import (
    WalkForwardSplitter,
)
from finai.infrastructure.modeling.trainer_factory import (
    create_model,
)


class TrainingService:
    def __init__(
        self,
        *,
        session: Session,
        model_output_directory: Path,
        mlflow_tracking_uri: str,
        mlflow_experiment_name: str,
    ) -> None:
        self._dataset_repository = DatasetVersionRepository(session)
        self._training_run_repository = TrainingRunRepository(session)
        self._evaluation_repository = EvaluationResultRepository(session)
        self._model_repository = ModelArtifactRepository(session)
        self._evaluation_service = EvaluationService()

        self._model_output_directory = model_output_directory

        self._mlflow_client = MLflowTrackingClient(
            tracking_uri=mlflow_tracking_uri,
            experiment_name=mlflow_experiment_name,
        )

    def train(
        self,
        *,
        dataset_id: UUID,
        model_type: ModelType,
        prediction_task: PredictionTask,
        feature_columns: list[str],
        parameters: dict,
        number_of_splits: int,
        test_size: int,
        random_seed: int,
    ):
        dataset = self._dataset_repository.get_by_id(dataset_id)

        if dataset is None:
            raise LookupError(f"Dataset not found: {dataset_id}")

        if dataset.status != "completed":
            raise ValueError("Only completed datasets can be trained.")

        if not dataset.storage_uri:
            raise ValueError("Dataset does not have a storage URI.")

        dataset_path = Path(dataset.storage_uri)

        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        frame = pd.read_parquet(dataset_path)
        frame = frame.sort_index()

        target_column = self._add_target(
            frame=frame,
            prediction_task=prediction_task,
        )

        validate_training_frame(
            frame=frame,
            feature_columns=feature_columns,
            target_column=target_column,
        )

        selected_frame = (
            frame[feature_columns + [target_column]]
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .dropna()
        )

        if selected_frame.empty:
            raise ValueError(
                "No usable training rows remain after removing missing and infinite values."
            )

        run = self._training_run_repository.create(
            dataset_id=dataset_id,
            model_type=model_type.value,
            prediction_task=prediction_task.value,
            target_column=target_column,
            feature_columns=feature_columns,
            parameters=parameters,
            number_of_splits=number_of_splits,
            test_size=test_size,
            random_seed=random_seed,
        )

        self._training_run_repository.mark_running(run)

        try:
            base_model = create_model(
                model_type=model_type,
                parameters=parameters,
                random_seed=random_seed,
            )

            splitter = WalkForwardSplitter(
                number_of_splits=number_of_splits,
                test_size=test_size,
            )

            fold_metrics: list[dict[str, float]] = []

            with self._mlflow_client.start_run(run_name=str(run.id)) as mlflow_run_id:
                self._mlflow_client.log_parameters(
                    {
                        "dataset_id": str(dataset_id),
                        "dataset_version": (dataset.version),
                        "model_type": (model_type.value),
                        "prediction_task": (prediction_task.value),
                        "target_column": (target_column),
                        "feature_columns": ",".join(feature_columns),
                        "number_of_splits": (number_of_splits),
                        "test_size": test_size,
                        "random_seed": random_seed,
                        **parameters,
                    }
                )

                for fold_number, (
                    training_indices,
                    validation_indices,
                ) in enumerate(
                    splitter.split(len(selected_frame)),
                    start=1,
                ):
                    training_frame = selected_frame.iloc[training_indices]

                    validation_frame = selected_frame.iloc[validation_indices]

                    model = self._build_pipeline(
                        model=clone(base_model),
                        model_type=model_type,
                    )

                    model.fit(
                        training_frame[feature_columns],
                        training_frame[target_column],
                    )

                    predictions = model.predict(validation_frame[feature_columns])

                    probabilities = None

                    if hasattr(
                        model,
                        "predict_proba",
                    ):
                        probability_matrix = model.predict_proba(validation_frame[feature_columns])

                        probabilities = probability_matrix[
                            :,
                            1,
                        ]

                    metrics = self._evaluation_service.evaluate(
                        prediction_task=(prediction_task),
                        targets=(validation_frame[target_column].to_numpy()),
                        predictions=np.asarray(predictions),
                        probabilities=(probabilities),
                    )

                    fold_metrics.append(metrics)

                    self._evaluation_repository.create(
                        training_run_id=run.id,
                        fold_number=fold_number,
                        metrics=metrics,
                        training_rows=len(training_frame),
                        validation_rows=len(validation_frame),
                    )

                aggregate_metrics = self._aggregate_metrics(fold_metrics)

                self._mlflow_client.log_metrics(aggregate_metrics)

                final_model = self._build_pipeline(
                    model=clone(base_model),
                    model_type=model_type,
                )

                final_model.fit(
                    selected_frame[feature_columns],
                    selected_frame[target_column],
                )

                model_path = self._save_model(
                    training_run_id=run.id,
                    model=final_model,
                )

                artifact_hash = self._calculate_file_hash(model_path)

                self._mlflow_client.log_artifact(str(model_path))

                artifact = self._model_repository.create(
                    training_run_id=run.id,
                    model_type=(model_type.value),
                    artifact_uri=str(model_path),
                    artifact_hash=(artifact_hash),
                    feature_columns=(feature_columns),
                    target_column=(target_column),
                    metadata_json={
                        "dataset_id": str(dataset.id),
                        "dataset_version": (dataset.version),
                        "prediction_task": (prediction_task.value),
                        "metrics": (aggregate_metrics),
                    },
                )

                self._training_run_repository.mark_completed(
                    run,
                    mlflow_run_id=mlflow_run_id,
                )

                return (
                    run,
                    artifact,
                    aggregate_metrics,
                )

        except Exception as error:
            self._training_run_repository.mark_failed(
                run,
                error_message=str(error),
            )

            raise

    @staticmethod
    def _add_target(
        *,
        frame: pd.DataFrame,
        prediction_task: PredictionTask,
    ) -> str:
        if "simple_return" not in frame.columns:
            raise ValueError("Dataset requires simple_return to generate a target.")

        future_return = frame["simple_return"].shift(-1)

        if prediction_task == PredictionTask.CLASSIFICATION:
            target_column = "target_positive_return"

            frame[target_column] = (future_return > 0).astype(float)

            frame.loc[
                future_return.isna(),
                target_column,
            ] = np.nan

            return target_column

        if prediction_task == PredictionTask.REGRESSION:
            target_column = "target_next_return"

            frame[target_column] = future_return

            return target_column

        raise ValueError(f"Unsupported prediction task: {prediction_task}")

    @staticmethod
    def _build_pipeline(
        *,
        model,
        model_type: ModelType,
    ) -> Pipeline:
        models_requiring_scaling = {
            ModelType.LOGISTIC_REGRESSION,
            ModelType.LINEAR_REGRESSION,
        }

        if model_type in models_requiring_scaling:
            return Pipeline(
                [
                    (
                        "scaler",
                        StandardScaler(),
                    ),
                    (
                        "model",
                        model,
                    ),
                ]
            )

        return Pipeline(
            [
                (
                    "model",
                    model,
                )
            ]
        )

    @staticmethod
    def _aggregate_metrics(
        fold_metrics: list[dict[str, float]],
    ) -> dict[str, float]:
        if not fold_metrics:
            raise ValueError("No fold metrics were generated.")

        metric_names = sorted({metric_name for metrics in fold_metrics for metric_name in metrics})

        return {
            metric_name: float(
                np.mean(
                    [metrics[metric_name] for metrics in fold_metrics if metric_name in metrics]
                )
            )
            for metric_name in metric_names
        }

    def _save_model(
        self,
        *,
        training_run_id: UUID,
        model,
    ) -> Path:
        self._model_output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = self._model_output_directory / f"{training_run_id}.joblib"

        joblib.dump(model, path)

        return path

    @staticmethod
    def _calculate_file_hash(
        path: Path,
    ) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as file_handle:
            for chunk in iter(
                lambda: file_handle.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()
