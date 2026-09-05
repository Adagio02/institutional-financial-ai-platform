from typing import Any

from sklearn.linear_model import LinearRegression


def create_linear_regression_model(
    *,
    parameters: dict[str, Any],
) -> LinearRegression:
    allowed_parameters = {
        "fit_intercept",
        "positive",
        "n_jobs",
    }

    filtered_parameters = {
        key: value for key, value in parameters.items() if key in allowed_parameters
    }

    return LinearRegression(**filtered_parameters)
