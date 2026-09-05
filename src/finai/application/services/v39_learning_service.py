from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v38_learning_service import (
    V38LearningCycleResult,
    V38LearningService,
)
from finai.domain.learning.v39_models import (
    create_v39_models,
)


class V39LearningService(
    V38LearningService
):
    def __init__(
        self,
        *,
        minimum_regime_rows: int,
        **kwargs: Any,
    ) -> None:
        if minimum_regime_rows < 100:
            raise ValueError(
                "minimum_regime_rows must "
                "be at least 100."
            )

        super().__init__(
            **kwargs
        )

        self._minimum_regime_rows = (
            minimum_regime_rows
        )

    def create_model_templates(
        self,
    ) -> dict[str, Any]:
        return create_v39_models(
            minimum_regime_rows=(
                self
                ._minimum_regime_rows
            )
        )

    @staticmethod
    def _patch_json(
        *,
        path: Path,
    ) -> None:
        if not path.exists():
            return

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            payload,
            dict,
        ):
            return

        payload[
            "version"
        ] = "3.9"

        payload[
            "learning_architecture"
        ] = (
            "regime_aware_ensemble"
        )

        payload[
            "regimes"
        ] = [
            "high_volatility",
            "trending",
            "range",
        ]

        path.write_text(
            json.dumps(
                payload,
                indent=2,
            ),
            encoding="utf-8",
        )

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V38LearningCycleResult:
        result = (
            super()
            .run_learning_cycle(
                symbol=symbol,
                interval=interval,
            )
        )

        candidate_metadata = Path(
            result
            .candidate_metadata_path
        )

        self._patch_json(
            path=(
                candidate_metadata
            )
        )

        artifact_directory = (
            candidate_metadata
            .parent
        )

        latest_path = (
            artifact_directory
            / "latest_learning_cycle.json"
        )

        self._patch_json(
            path=latest_path
        )

        champion_metadata = (
            artifact_directory
            / "champion.json"
        )

        if result.promoted:
            self._patch_json(
                path=(
                    champion_metadata
                )
            )

        return result