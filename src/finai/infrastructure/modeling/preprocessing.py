from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


@dataclass(slots=True)
class PreparedTrainingData:
    features: pd.DataFrame
    target: pd.Series


def prepare_training_data(
    frame: pd.DataFrame,
    *,
    feature_columns: list[str],
    target_column: str,
) -> PreparedTrainingData:
    selected = frame[feature_columns + [target_column]].copy()

    selected = selected.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    selected = selected.dropna()

    return PreparedTrainingData(
        features=selected[feature_columns],
        target=selected[target_column],
    )


def fit_scaler(
    training_features: pd.DataFrame,
) -> StandardScaler:
    scaler = StandardScaler()
    scaler.fit(training_features)

    return scaler
