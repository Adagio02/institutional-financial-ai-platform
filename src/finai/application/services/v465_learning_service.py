from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    precision_score,
)

from finai.application.services.v464_learning_service import (
    V464LearningService,
)
from finai.domain.learning.v44_research import (
    split_discovery_locked_final,
    write_json,
)
from finai.domain.learning.v46_events import (
    META_FEATURE_COLUMNS,
    apply_event_family,
)
from finai.domain.learning.v46_models import (
    create_meta_model,
)
from finai.domain.learning.v46_research import (
    candidate_hash,
)


class V465LearningService(V464LearningService):
    VERSION = "4.6.5"
    LEARNING_ARCHITECTURE = (
        "frozen_event_meta_locked_validation"
    )

    def __init__(
        self,
        *,
        v465_artifact_directory: str = "artifacts/v465",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v465_artifact_directory = Path(
            v465_artifact_directory
        )
        self._v465_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def run_locked_validation(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        output_path = (
            self._v465_artifact_directory
            / "v465_locked_validation.json"
        )

        if output_path.exists():
            raise RuntimeError(
                "V4.6.5 locked validation was already "
                "opened. Do not rerun the same locked "
                "period."
            )

        frozen_path = (
            self._v464_artifact_directory
            / "v464_frozen_candidate.json"
        )

        if not frozen_path.exists():
            raise FileNotFoundError(
                "Run V4.6.4 first."
            )

        frozen = json.loads(
            frozen_path.read_text(
                encoding="utf-8"
            )
        )

        if not frozen.get(
            "frozen",
            False,
        ):
            raise RuntimeError(
                "No qualified frozen candidate exists."
            )

        candidate = dict(
            frozen["candidate"]
        )

        if (
            candidate_hash(candidate)
            != frozen[
                "candidate_sha256"
            ]
        ):
            raise RuntimeError(
                "Frozen candidate hash mismatch."
            )

        horizon = int(
            candidate["horizon_bars"]
        )
        family = str(
            candidate["event_family"]
        )
        threshold = float(
            candidate[
                "selected_threshold"
            ]
        )
        model_config = dict(
            candidate[
                "model_config"
            ]
        )

        dataset, rows_loaded = (
            self._dataset_for_horizon(
                symbol=symbol,
                interval=interval,
                horizon_bars=horizon,
            )
        )

        discovery, locked, _ = (
            split_discovery_locked_final(
                dataset
            )
        )

        discovery_frame = (
            apply_event_family(
                discovery,
                family=family,
                round_trip_cost_bps=(
                    self._v41_round_trip_cost_bps
                ),
            )
        )

        locked_frame = (
            apply_event_family(
                locked,
                family=family,
                round_trip_cost_bps=(
                    self._v41_round_trip_cost_bps
                ),
            )
        )

        training_events = (
            discovery_frame.loc[
                discovery_frame[
                    "event_direction"
                ]
                != 0
            ]
            .copy()
        )

        if (
            len(training_events) < 100
            or training_events[
                "meta_target"
            ].nunique()
            < 2
        ):
            raise RuntimeError(
                "Frozen candidate has insufficient "
                "discovery events for final fitting."
            )

        model = create_meta_model(
            model_config
        )
        model.fit(
            training_events[
                META_FEATURE_COLUMNS
            ],
            training_events[
                "meta_target"
            ],
        )

        event_mask = (
            locked_frame[
                "event_direction"
            ]
            != 0
        )

        events = locked_frame.loc[
            event_mask
        ].copy()

        positions = np.zeros(
            len(locked_frame),
            dtype=int,
        )

        if (
            len(events) > 0
            and threshold < 1.0
        ):
            take_probability = (
                self._take_probability(
                    model,
                    events,
                )
            )
            selected = (
                take_probability
                >= threshold
            )

            event_indices = np.flatnonzero(
                event_mask.to_numpy()
            )

            positions[
                event_indices[selected]
            ] = (
                events.loc[
                    selected,
                    "event_direction",
                ]
                .to_numpy(dtype=int)
            )

            actual = events[
                "meta_target"
            ].to_numpy(dtype=int)
            predicted = (
                take_probability
                >= threshold
            ).astype(int)

            meta_balanced_accuracy = float(
                balanced_accuracy_score(
                    actual,
                    predicted,
                )
            )
            meta_f1 = float(
                f1_score(
                    actual,
                    predicted,
                    zero_division=0,
                )
            )
            meta_precision = float(
                precision_score(
                    actual,
                    predicted,
                    zero_division=0,
                )
            )

        else:
            meta_balanced_accuracy = 0.5
            meta_f1 = 0.0
            meta_precision = 0.0

        backtest = self.simulate(
            positions=positions,
            forward_returns=locked_frame[
                "forward_return"
            ].to_numpy(dtype=float),
        )

        locked_qualified = (
            backtest.net_return > 0.0
            and backtest.trade_count
            >= self._minimum_trades
            and backtest.maximum_drawdown
            <= self._maximum_holdout_drawdown
            and meta_balanced_accuracy
            >= 0.52
            and meta_precision
            >= 0.50
        )

        payload = {
            "version": self.VERSION,
            "symbol": symbol.upper(),
            "interval": interval.lower(),
            "rows_loaded": int(
                rows_loaded
            ),
            "candidate": candidate,
            "candidate_sha256": frozen[
                "candidate_sha256"
            ],
            "locked_validation_opened": True,
            "final_test_opened": False,
            "locked_event_rows": int(
                len(events)
            ),
            "locked_meta_balanced_accuracy": (
                meta_balanced_accuracy
            ),
            "locked_meta_f1": meta_f1,
            "locked_meta_precision": (
                meta_precision
            ),
            "locked_net_return": float(
                backtest.net_return
            ),
            "locked_trade_count": int(
                backtest.trade_count
            ),
            "locked_maximum_drawdown": float(
                backtest.maximum_drawdown
            ),
            "locked_sharpe_like": float(
                backtest.sharpe_like
            ),
            "locked_qualified": bool(
                locked_qualified
            ),
            "champion_promoted": False,
            "next_step": (
                "one-shot untouched final test"
                if locked_qualified
                else
                "stop; do not open final test"
            ),
        }

        write_json(
            output_path,
            payload,
        )

        return payload
