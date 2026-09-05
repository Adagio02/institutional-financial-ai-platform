import numpy as np

from finai.domain.modeling.enums import (
    PredictionTask,
)
from finai.domain.modeling.metrics import (
    calculate_classification_metrics,
    calculate_regression_metrics,
)


class EvaluationService:
    def evaluate(
        self,
        *,
        prediction_task: PredictionTask,
        targets: np.ndarray,
        predictions: np.ndarray,
        probabilities: np.ndarray | None = None,
    ) -> dict[str, float]:
        if prediction_task == PredictionTask.CLASSIFICATION:
            return calculate_classification_metrics(
                targets=targets,
                predictions=predictions,
                probabilities=probabilities,
            )

        if prediction_task == PredictionTask.REGRESSION:
            return calculate_regression_metrics(
                targets=targets,
                predictions=predictions,
            )

        raise ValueError(f"Unsupported prediction task: {prediction_task}")
