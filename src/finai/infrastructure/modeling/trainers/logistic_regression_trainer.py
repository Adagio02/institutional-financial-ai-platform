from typing import Any

from sklearn.linear_model import LogisticRegression


def create_logistic_regression_model(
    *,
    parameters: dict[str, Any],
    random_seed: int,
) -> LogisticRegression:
    allowed_parameters = {
        "C",
        "class_weight",
        "max_iter",
        "solver",
    }

    filtered_parameters = {k: v for k, v in parameters.items() if k in allowed_parameters}

    filtered_parameters.setdefault(
        "max_iter",
        1000,
    )

    return LogisticRegression(
        random_state=random_seed,
        **filtered_parameters,
    )
