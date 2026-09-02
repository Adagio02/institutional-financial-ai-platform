from __future__ import annotations

from pathlib import Path
from typing import Any

from finai.application.services.v45_learning_service import (
    V45LearningService,
)
from finai.domain.learning.v44_research import (
    split_discovery_locked_final,
    write_json,
)
from finai.domain.learning.v45_features import (
    V421_FEATURE_COLUMNS,
    V45_ENGINEERED_FEATURE_COLUMNS,
    V45_FEATURE_FAMILIES,
)


class V451LearningService(V45LearningService):
    VERSION = "4.5.1"
    LEARNING_ARCHITECTURE = (
        "causal_feature_family_ablation_"
        "discovery_only"
    )

    def __init__(
        self,
        *,
        v451_artifact_directory: str = (
            "artifacts/v451"
        ),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v451_artifact_directory = Path(
            v451_artifact_directory
        )
        self._v451_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _variants(
        self,
    ) -> dict[str, list[str]]:
        baseline = list(
            V421_FEATURE_COLUMNS
        )
        return {
            "baseline": baseline,
            "baseline_plus_price_structure": (
                baseline
                + list(
                    V45_FEATURE_FAMILIES[
                        "price_structure"
                    ]
                )
            ),
            "baseline_plus_volume_structure": (
                baseline
                + list(
                    V45_FEATURE_FAMILIES[
                        "volume_structure"
                    ]
                )
            ),
            "baseline_plus_market_relative": (
                baseline
                + list(
                    V45_FEATURE_FAMILIES[
                        "market_relative"
                    ]
                )
            ),
            "baseline_plus_session_state": (
                baseline
                + list(
                    V45_FEATURE_FAMILIES[
                        "session_state"
                    ]
                )
            ),
            "baseline_plus_regime_state": (
                baseline
                + list(
                    V45_FEATURE_FAMILIES[
                        "regime_state"
                    ]
                )
            ),
            "all_engineered": (
                baseline
                + list(
                    V45_ENGINEERED_FEATURE_COLUMNS
                )
            ),
        }

    def run_feature_ablation(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
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

        for variant, columns in (
            self._variants().items()
        ):
            for model_name, template in (
                models.items()
            ):
                result = self.evaluate_feature_set(
                    model_name=model_name,
                    model_template=template,
                    research=discovery,
                    feature_columns=columns,
                    direction="both",
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
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "leaderboard": leaderboard,
        }
        write_json(
            self._v451_artifact_directory
            / "v451_feature_ablation.json",
            payload,
        )
        return payload
