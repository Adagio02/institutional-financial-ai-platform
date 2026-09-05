import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)


def calculate_classification_metrics(
    *,
    targets: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray | None = None,
) -> dict[str, float]:
    metrics = {
        "accuracy": float(accuracy_score(targets, predictions)),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                targets,
                predictions,
            )
        ),
        "precision": float(
            precision_score(
                targets,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                targets,
                predictions,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                targets,
                predictions,
                zero_division=0,
            )
        ),
    }

    if probabilities is not None:
        unique_targets = np.unique(targets)

        if len(unique_targets) == 2:
            metrics["roc_auc"] = float(
                roc_auc_score(
                    targets,
                    probabilities,
                )
            )

            metrics["brier_score"] = float(
                brier_score_loss(
                    targets,
                    probabilities,
                )
            )

    return metrics


def calculate_regression_metrics(
    *,
    targets: np.ndarray,
    predictions: np.ndarray,
) -> dict[str, float]:
    return {
        "mae": float(
            mean_absolute_error(
                targets,
                predictions,
            )
        ),
        "rmse": float(
            mean_squared_error(
                targets,
                predictions,
            )
            ** 0.5
        ),
        "r_squared": float(
            r2_score(
                targets,
                predictions,
            )
        ),
        "directional_accuracy": float(np.mean(np.sign(targets) == np.sign(predictions))),
    }
