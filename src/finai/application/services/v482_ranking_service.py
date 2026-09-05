from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone

from finai.domain.learning.v481_targets import V481_TARGET_COLUMNS
from finai.domain.learning.v482_ranking import deterministic_sample, walk_forward_predictions
from finai.domain.learning.v48_features import V48_RANK_FEATURE_COLUMNS, V48_ZSCORE_FEATURE_COLUMNS
from finai.domain.learning.v48_models import create_v48_models
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


V482_MODEL_FEATURE_COLUMNS = V48_RANK_FEATURE_COLUMNS + V48_ZSCORE_FEATURE_COLUMNS
V482_RETURN_TARGETS = [V481_TARGET_COLUMNS[0], V481_TARGET_COLUMNS[1]]


class V482RankingService:
    VERSION = "4.8.2"

    def __init__(
        self,
        *,
        source_path: str = "artifacts/v481/v481_neutral_target_panel",
        artifact_directory: str = "artifacts/v482",
        fold_count: int = 5,
        purge_timestamps: int = 30,
        maximum_training_rows: int = 250_000,
        prediction_stride: int = 30,
    ) -> None:
        self._source_path = Path(source_path)
        self._artifact_directory = Path(artifact_directory)
        self._fold_count = int(fold_count)
        self._purge_timestamps = int(purge_timestamps)
        self._maximum_training_rows = int(maximum_training_rows)
        self._prediction_stride = int(prediction_stride)

    def run(self) -> dict[str, Any]:
        try:
            frame = read_research_frame(self._source_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V4.8.1 before V4.8.2.") from exc
        templates = create_v48_models()
        prediction_frames: list[pd.DataFrame] = []
        fold_reports: list[dict[str, Any]] = []
        fitted_models: dict[str, Any] = {}

        for target_index, target in enumerate(V482_RETURN_TARGETS):
            predictions, reports = walk_forward_predictions(
                frame,
                feature_columns=V482_MODEL_FEATURE_COLUMNS,
                target_column=target,
                models=templates,
                fold_count=self._fold_count,
                purge_timestamps=self._purge_timestamps,
                maximum_training_rows=self._maximum_training_rows,
                prediction_stride=self._prediction_stride,
            )
            prediction_frames.append(predictions)
            fold_reports.extend(reports)
            finite = frame.replace([np.inf, -np.inf], np.nan).dropna(
                subset=[target, *V482_MODEL_FEATURE_COLUMNS]
            )
            training = deterministic_sample(
                finite,
                maximum_rows=self._maximum_training_rows,
                random_state=4890 + target_index,
            )
            for model_name, template in templates.items():
                estimator = clone(template)
                estimator.fit(
                    training[V482_MODEL_FEATURE_COLUMNS].to_numpy(dtype=np.float32),
                    training[target].to_numpy(dtype=np.float32),
                )
                fitted_models[f"{target}::{model_name}"] = estimator

        combined = pd.concat(prediction_frames, ignore_index=True)
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        prediction_path = write_research_frame(
            combined, self._artifact_directory / "v482_oos_predictions"
        )
        model_path = self._artifact_directory / "v482_ranking_models.joblib"
        joblib.dump(
            {
                "version": self.VERSION,
                "feature_columns": V482_MODEL_FEATURE_COLUMNS,
                "models": fitted_models,
            },
            model_path,
            compress=3,
        )
        payload = {
            "version": self.VERSION,
            "stage": "cross_sectional_ranking_models",
            "source_path": str(self._source_path),
            "prediction_path": str(prediction_path),
            "model_path": str(model_path),
            "feature_columns": V482_MODEL_FEATURE_COLUMNS,
            "target_columns": V482_RETURN_TARGETS,
            "model_names": list(templates),
            "fold_count": self._fold_count,
            "purge_timestamps": self._purge_timestamps,
            "maximum_training_rows": self._maximum_training_rows,
            "prediction_stride": self._prediction_stride,
            "out_of_sample_prediction_rows": int(len(combined)),
            "fold_results": fold_reports,
            "research_only": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Run V4.8.3 signal IC and rank-IC analysis.",
        }
        (self._artifact_directory / "v482_training_report.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload
