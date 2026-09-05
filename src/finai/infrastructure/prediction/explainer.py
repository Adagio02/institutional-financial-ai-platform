from typing import Any

import numpy as np
import pandas as pd


def calculate_feature_contributions(
    *,
    model: Any,
    feature_frame: pd.DataFrame,
) -> tuple[float | None, dict[str, float], dict]:
    final_estimator = model

    if hasattr(model, "named_steps"):
        final_estimator = model.named_steps.get(
            "model",
            model,
        )

    transformed_values = feature_frame.to_numpy(dtype=float)

    if hasattr(model, "named_steps"):
        scaler = model.named_steps.get("scaler")

        if scaler is not None:
            transformed_values = scaler.transform(feature_frame)

    if hasattr(final_estimator, "coef_"):
        coefficients = np.asarray(final_estimator.coef_)

        if coefficients.ndim == 2:
            coefficients = coefficients[0]

        contributions = {
            feature_name: float(transformed_values[0][index] * coefficients[index])
            for index, feature_name in enumerate(feature_frame.columns)
        }

        intercept = getattr(
            final_estimator,
            "intercept_",
            None,
        )

        baseline = None

        if intercept is not None:
            baseline = float(np.asarray(intercept).reshape(-1)[0])

        return (
            baseline,
            contributions,
            {
                "method": "linear_coefficient_contribution",
            },
        )

    if hasattr(final_estimator, "feature_importances_"):
        importances = np.asarray(final_estimator.feature_importances_)

        contributions = {
            feature_name: float(importances[index])
            for index, feature_name in enumerate(feature_frame.columns)
        }

        return (
            None,
            contributions,
            {
                "method": "tree_feature_importance",
                "warning": (
                    "Tree feature importance is global and is not a local causal explanation."
                ),
            },
        )

    raise ValueError("The model type does not support the configured explanation method.")
