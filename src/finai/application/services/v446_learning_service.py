from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from finai.application.services.v445_learning_service import (
    V445LearningService,
)
from finai.domain.learning.v44_research import (
    split_discovery_locked_final,
    write_json,
)


class V446LearningService(V445LearningService):
    """
    V4.4.6: focused recent-window signal research.

    Instead of brute-forcing new model families, V4.4.6 takes the
    strongest positive-return V4.4.2 discovery candidates and asks
    whether their signal becomes more temporally stable when the
    research sample is restricted to a recent causal window.

    IMPORTANT:
      - only the discovery partition is used;
      - locked validation is not opened;
      - final test is not opened;
      - governance gates are not weakened;
      - transaction-cost assumptions are inherited unchanged.
    """

    VERSION = "4.4.6"
    LEARNING_ARCHITECTURE = (
        "focused_recent_window_"
        "discovery_only_signal_research"
    )

    RECENT_WINDOW_ROWS = (
        None,
        20_000,
        40_000,
    )

    def __init__(
        self,
        *,
        v446_artifact_directory: str = (
            "artifacts/v446"
        ),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v446_artifact_directory = Path(
            v446_artifact_directory
        )
        self._v446_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _load_v445_payload(
        self,
    ) -> dict[str, Any]:
        path = (
            self._v445_artifact_directory
            / "v445_stability_diagnostics.json"
        )

        if not path.exists():
            raise FileNotFoundError(
                "V4.4.5 artifact is required: "
                f"{path}"
            )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(payload, dict):
            raise RuntimeError(
                "V4.4.5 artifact must contain "
                "a JSON object."
            )

        return payload

    def _set_target_definition(
        self,
        *,
        horizon_bars: int,
        edge_bps: float,
    ) -> tuple[int, float]:
        """
        Use the actual inherited attribute names from the V4.3/V4.4
        project line. V4.4 originally failed because it used the
        nonexistent `_minimum_edge_bps`.
        """
        original_horizon = int(
            self._forward_horizon_bars
        )
        original_edge = float(
            self._target_minimum_edge_bps
        )

        self._forward_horizon_bars = int(
            horizon_bars
        )
        self._target_minimum_edge_bps = float(
            edge_bps
        )

        return (
            original_horizon,
            original_edge,
        )

    def _restore_target_definition(
        self,
        state: tuple[int, float],
    ) -> None:
        (
            original_horizon,
            original_edge,
        ) = state

        self._forward_horizon_bars = (
            original_horizon
        )
        self._target_minimum_edge_bps = (
            original_edge
        )

    def _dataset_for_target(
        self,
        *,
        symbol: str,
        interval: str,
        horizon_bars: int,
        edge_bps: float,
    ):
        state = self._set_target_definition(
            horizon_bars=horizon_bars,
            edge_bps=edge_bps,
        )

        try:
            return self.build_dataset(
                symbol=symbol,
                interval=interval,
                include_target=True,
            )
        finally:
            self._restore_target_definition(
                state
            )

    def run_focused_discovery(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        normalized_symbol = (
            symbol.strip().upper()
        )
        normalized_interval = (
            interval.strip().lower()
        )

        v445 = self._load_v445_payload()
        focused = list(
            v445.get(
                "focused_candidates",
                [],
            )
        )

        if not focused:
            raise RuntimeError(
                "V4.4.5 produced no focused "
                "research candidates."
            )

        leaderboard: list[
            dict[str, Any]
        ] = []

        for candidate in focused:
            horizon = int(
                candidate["horizon_bars"]
            )
            edge = float(
                candidate["edge_bps"]
            )
            model_name = str(
                candidate["model_name"]
            )

            dataset, rows_loaded = (
                self._dataset_for_target(
                    symbol=normalized_symbol,
                    interval=normalized_interval,
                    horizon_bars=horizon,
                    edge_bps=edge,
                )
            )

            discovery, _, _ = (
                split_discovery_locked_final(
                    dataset
                )
            )

            model_templates = (
                self.create_model_templates()
            )

            if (
                model_name
                not in model_templates
            ):
                raise KeyError(
                    "Focused model is unavailable "
                    f"in current templates: "
                    f"{model_name}"
                )

            for window_rows in (
                self.RECENT_WINDOW_ROWS
            ):
                if window_rows is None:
                    research = (
                        discovery.copy()
                    )
                    window_label = (
                        "full_discovery"
                    )
                else:
                    if (
                        len(discovery)
                        <= window_rows
                    ):
                        research = (
                            discovery.copy()
                        )
                    else:
                        research = (
                            discovery.iloc[
                                -window_rows:
                            ].copy()
                        )
                    window_label = (
                        f"recent_{window_rows}"
                    )

                state = (
                    self._set_target_definition(
                        horizon_bars=horizon,
                        edge_bps=edge,
                    )
                )

                try:
                    evaluation = (
                        self.evaluate_model(
                            model_name=(
                                model_name
                            ),
                            model_template=(
                                model_templates[
                                    model_name
                                ]
                            ),
                            research=research,
                        )
                    )
                finally:
                    (
                        self
                        ._restore_target_definition(
                            state
                        )
                    )

                leaderboard.append(
                    {
                        "source_config_key": (
                            candidate[
                                "config_key"
                            ]
                        ),
                        "model_name": (
                            model_name
                        ),
                        "horizon_bars": (
                            horizon
                        ),
                        "edge_bps": edge,
                        "window": (
                            window_label
                        ),
                        "window_rows_requested": (
                            window_rows
                        ),
                        "research_rows": int(
                            len(research)
                        ),
                        "rows_loaded": int(
                            rows_loaded
                        ),
                        "long_threshold": float(
                            evaluation
                            .long_threshold
                        ),
                        "short_threshold": float(
                            evaluation
                            .short_threshold
                        ),
                        "balanced_accuracy": float(
                            evaluation
                            .balanced_accuracy
                        ),
                        "macro_f1": float(
                            evaluation
                            .macro_f1
                        ),
                        "net_return": float(
                            evaluation
                            .net_return
                        ),
                        "trade_count": int(
                            evaluation
                            .trade_count
                        ),
                        "maximum_drawdown": float(
                            evaluation
                            .maximum_drawdown
                        ),
                        "sharpe_like": float(
                            evaluation
                            .sharpe_like
                        ),
                        "positive_fold_fraction": float(
                            evaluation
                            .positive_fold_fraction
                        ),
                        "worst_fold_return": float(
                            evaluation
                            .worst_fold_return
                        ),
                        "fold_returns": [
                            float(
                                fold.net_return
                            )
                            for fold
                            in evaluation.folds
                        ],
                    }
                )

        ranked = sorted(
            leaderboard,
            key=lambda item: (
                item["positive_fold_fraction"],
                item["net_return"],
                -item["maximum_drawdown"],
            ),
            reverse=True,
        )

        payload = {
            "version": self.VERSION,
            "symbol": normalized_symbol,
            "interval": normalized_interval,
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "window_method": (
                "recent discovery truncation; "
                "inherited walk-forward evaluation "
                "remains unchanged inside each "
                "research sample"
            ),
            "governance_weakened": False,
            "candidate_count": len(
                ranked
            ),
            "leaderboard": ranked,
        }

        write_json(
            self._v446_artifact_directory
            / "v446_focused_discovery.json",
            payload,
        )

        return payload
