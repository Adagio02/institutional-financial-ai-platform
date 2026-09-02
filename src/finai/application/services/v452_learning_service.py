from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v451_learning_service import (
    V451LearningService,
)
from finai.domain.learning.v44_research import (
    split_discovery_locked_final,
    write_json,
)
from finai.domain.learning.v45_research import (
    DIRECTIONS,
)


class V452LearningService(V451LearningService):
    VERSION = "4.5.2"
    LEARNING_ARCHITECTURE = (
        "directional_feature_candidate_"
        "discovery_only"
    )

    def __init__(
        self,
        *,
        v452_artifact_directory: str = (
            "artifacts/v452"
        ),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v452_artifact_directory = Path(
            v452_artifact_directory
        )
        self._v452_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _load_ablation(
        self,
    ) -> dict[str, Any]:
        path = (
            self._v451_artifact_directory
            / "v451_feature_ablation.json"
        )
        if not path.exists():
            raise FileNotFoundError(
                "Run V4.5.1 first: "
                f"{path}"
            )
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def run_directional_research(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        ablation = self._load_ablation()
        source = list(
            ablation.get(
                "leaderboard",
                [],
            )
        )

        # Use discovery evidence only to narrow the experiment.
        # Deduplicate variant/model pairs and keep at most 8.
        selected: list[
            tuple[str, str, list[str]]
        ] = []
        seen: set[
            tuple[str, str]
        ] = set()

        for item in source:
            key = (
                str(item["variant"]),
                str(item["model_name"]),
            )
            if key in seen:
                continue
            if (
                float(
                    item.get(
                        "net_return",
                        0.0,
                    )
                )
                <= 0.0
            ):
                continue
            seen.add(key)
            selected.append(
                (
                    key[0],
                    key[1],
                    list(
                        item[
                            "feature_columns"
                        ]
                    ),
                )
            )
            if len(selected) >= 8:
                break

        if not selected:
            payload = {
                "version": self.VERSION,
                "status": (
                    "no_positive_ablation_candidate"
                ),
                "research_only": True,
                "locked_validation_opened": False,
                "final_test_opened": False,
                "leaderboard": [],
            }
            write_json(
                self._v452_artifact_directory
                / "v452_directional_research.json",
                payload,
            )
            return payload

        dataset, rows_loaded = self.build_dataset(
            symbol=symbol,
            interval=interval,
            include_target=True,
        )
        discovery, _, _ = (
            split_discovery_locked_final(
                dataset
            )
        )
        models = self.create_model_templates()
        leaderboard: list[
            dict[str, Any]
        ] = []

        for (
            variant,
            model_name,
            columns,
        ) in selected:
            if model_name not in models:
                continue

            for direction in DIRECTIONS:
                result = self.evaluate_feature_set(
                    model_name=model_name,
                    model_template=(
                        models[model_name]
                    ),
                    research=discovery,
                    feature_columns=columns,
                    direction=direction,
                )
                result["variant"] = variant
                result["feature_columns"] = (
                    columns
                )
                leaderboard.append(result)

        leaderboard.sort(
            key=lambda item: (
                item[
                    "positive_fold_fraction"
                ],
                item["net_return"],
                -item[
                    "maximum_drawdown"
                ],
            ),
            reverse=True,
        )

        payload = {
            "version": self.VERSION,
            "symbol": symbol.upper(),
            "interval": interval.lower(),
            "rows_loaded": int(rows_loaded),
            "source_candidate_count": len(
                selected
            ),
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "leaderboard": leaderboard,
        }
        write_json(
            self._v452_artifact_directory
            / "v452_directional_research.json",
            payload,
        )
        return payload
