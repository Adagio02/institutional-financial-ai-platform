from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error


@dataclass(frozen=True, slots=True)
class RankingFold:
    fold: int
    train_timestamps: np.ndarray
    validation_timestamps: np.ndarray


def chronological_ranking_folds(
    frame: pd.DataFrame,
    *,
    fold_count: int = 5,
    purge_timestamps: int = 30,
) -> list[RankingFold]:
    if fold_count < 2:
        raise ValueError("fold_count must be at least 2.")
    if purge_timestamps < 0:
        raise ValueError("purge_timestamps cannot be negative.")
    timestamps = np.array(sorted(pd.to_datetime(frame["timestamp"], utc=True).unique()))
    if len(timestamps) < (fold_count + 1) * 10 + purge_timestamps:
        raise ValueError("Not enough timestamps for V4.8.2 walk-forward folds.")
    blocks = np.array_split(timestamps, fold_count + 1)
    folds: list[RankingFold] = []
    for index in range(fold_count):
        train_times = np.concatenate(blocks[: index + 1])
        if purge_timestamps:
            train_times = train_times[:-purge_timestamps]
        validation_times = blocks[index + 1]
        if not len(train_times) or not len(validation_times):
            raise RuntimeError("V4.8.2 produced an empty chronological fold.")
        folds.append(RankingFold(index + 1, train_times, validation_times))
    return folds


def finite_training_frame(
    frame: pd.DataFrame,
    *,
    feature_columns: list[str],
    target_column: str,
) -> pd.DataFrame:
    required = ["timestamp", "symbol", "sector", target_column, *feature_columns]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("V4.8.2 dataset missing: " + ", ".join(missing))
    output = frame[required].copy().replace([np.inf, -np.inf], np.nan)
    return output.dropna(subset=[target_column, *feature_columns])


def deterministic_sample(
    frame: pd.DataFrame,
    *,
    maximum_rows: int,
    random_state: int,
) -> pd.DataFrame:
    if maximum_rows < 1:
        raise ValueError("maximum_rows must be positive.")
    if len(frame) <= maximum_rows:
        return frame
    return frame.sample(n=maximum_rows, replace=False, random_state=random_state).sort_values(
        ["timestamp", "symbol"]
    )


def walk_forward_predictions(
    frame: pd.DataFrame,
    *,
    feature_columns: list[str],
    target_column: str,
    models: dict[str, Any],
    fold_count: int = 5,
    purge_timestamps: int = 30,
    maximum_training_rows: int = 250_000,
    prediction_stride: int = 1,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    if prediction_stride < 1:
        raise ValueError("prediction_stride must be positive.")
    usable = finite_training_frame(
        frame, feature_columns=feature_columns, target_column=target_column
    )
    usable_times = pd.to_datetime(usable["timestamp"], utc=True)
    folds = chronological_ranking_folds(
        usable, fold_count=fold_count, purge_timestamps=purge_timestamps
    )
    predictions: list[pd.DataFrame] = []
    reports: list[dict[str, Any]] = []
    for model_index, (model_name, template) in enumerate(models.items()):
        for fold in folds:
            train = usable.loc[usable_times.isin(set(fold.train_timestamps))]
            prediction_times = fold.validation_timestamps[::prediction_stride]
            validation = usable.loc[usable_times.isin(set(prediction_times))]
            train = deterministic_sample(
                train,
                maximum_rows=maximum_training_rows,
                random_state=4820 + model_index * 100 + fold.fold,
            )
            estimator = clone(template)
            estimator.fit(
                train[feature_columns].to_numpy(dtype=np.float32),
                train[target_column].to_numpy(dtype=np.float32),
            )
            values = estimator.predict(
                validation[feature_columns].to_numpy(dtype=np.float32)
            )
            block = validation[["timestamp", "symbol", "sector", target_column]].copy()
            block["model_name"] = model_name
            block["target_column"] = target_column
            block["fold"] = fold.fold
            block["prediction"] = values
            predictions.append(block)
            reports.append({
                "model_name": model_name,
                "target_column": target_column,
                "fold": fold.fold,
                "training_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                "training_end": str(fold.train_timestamps[-1]),
                "validation_start": str(fold.validation_timestamps[0]),
                "validation_end": str(fold.validation_timestamps[-1]),
                "rmse": float(np.sqrt(mean_squared_error(validation[target_column], values))),
                "mae": float(mean_absolute_error(validation[target_column], values)),
            })
    if not predictions:
        raise RuntimeError("V4.8.2 did not produce out-of-sample predictions.")
    return pd.concat(predictions, ignore_index=True), reports
