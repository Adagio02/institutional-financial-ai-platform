from __future__ import annotations

import json
import shutil
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from finai.application.services.v40_learning_service import (
    V40LearningService,
)
from finai.domain.learning.v38_features import (
    V38_FEATURE_COLUMNS,
)


class V40ShadowService:
    def __init__(
        self,
        *,
        learning_service: V40LearningService,
        shadow_directory: str,
        minimum_observations: int,
        minimum_trades: int,
        minimum_net_return: float,
        maximum_drawdown: float,
    ) -> None:
        if minimum_observations < 1:
            raise ValueError(
                "minimum_observations must be positive."
            )

        if minimum_trades < 1:
            raise ValueError(
                "minimum_trades must be positive."
            )

        if maximum_drawdown < 0.0:
            raise ValueError(
                "maximum_drawdown cannot be negative."
            )

        self._learning_service = (
            learning_service
        )

        self._shadow_directory = Path(
            shadow_directory
        )

        self._shadow_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._minimum_observations = (
            minimum_observations
        )

        self._minimum_trades = (
            minimum_trades
        )

        self._minimum_net_return = (
            minimum_net_return
        )

        self._maximum_drawdown_limit = (
            maximum_drawdown
        )

    @property
    def model_path(
        self,
    ) -> Path:
        return (
            self._shadow_directory
            / "shadow_candidate.joblib"
        )

    @property
    def metadata_path(
        self,
    ) -> Path:
        return (
            self._shadow_directory
            / "shadow_candidate.json"
        )

    @property
    def observations_path(
        self,
    ) -> Path:
        return (
            self._shadow_directory
            / "observations.jsonl"
        )

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                "Invalid shadow metadata."
            )

        return payload

    @staticmethod
    def _write_json(
        *,
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )

    def _append_observation(
        self,
        payload: dict[str, Any],
    ) -> None:
        self.observations_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.observations_path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    payload,
                    sort_keys=True,
                    default=str,
                )
            )

            handle.write("\n")

    @staticmethod
    def _calculate_maximum_drawdown(
        returns: np.ndarray,
    ) -> float:
        if len(returns) == 0:
            return 0.0

        equity = np.cumprod(
            1.0 + returns
        )

        running_maximum = (
            np.maximum.accumulate(
                equity
            )
        )

        drawdowns = (
            equity
            / running_maximum
            - 1.0
        )

        return float(
            abs(
                np.min(
                    drawdowns
                )
            )
        )

    def _promote(
        self,
        *,
        metadata: dict[str, Any],
    ) -> None:
        champion_path = (
            self._learning_service
            .champion_path
        )

        champion_metadata_path = (
            self._learning_service
            .champion_metadata_path
        )

        champion_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copyfile(
            self.model_path,
            champion_path,
        )

        champion_metadata = dict(
            metadata
        )

        champion_metadata.update(
            {
                "version": "4.0",
                "model_path": str(
                    champion_path
                ),
                "shadow_status": "promoted",
                "promoted": True,
                "promotion_reason": (
                    "Candidate passed V4.0 "
                    "prospective shadow validation."
                ),
                "promoted_at": (
                    datetime.now(
                        UTC
                    ).isoformat()
                ),
            }
        )

        self._write_json(
            path=champion_metadata_path,
            payload=champion_metadata,
        )

    def run_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        if not self.model_path.exists():
            return {
                "status": (
                    "no_shadow_candidate"
                ),
            }

        if not self.metadata_path.exists():
            return {
                "status": (
                    "no_shadow_metadata"
                ),
            }

        metadata = self._load_json(
            self.metadata_path
        )

        if metadata.get(
            "shadow_status"
        ) == "promoted":
            return {
                "status": "already_promoted",
                "candidate_id": (
                    metadata.get(
                        "candidate_id"
                    )
                ),
            }

        dataset, _ = (
            self._learning_service
            .build_dataset(
                symbol=symbol,
                interval=interval,
                include_target=True,
            )
        )

        if dataset.empty:
            return {
                "status": "no_dataset",
            }

        shadow_started_at = (
            metadata.get(
                "shadow_started_at"
            )
        )

        if not shadow_started_at:
            raise RuntimeError(
                "shadow_started_at is missing."
            )

        started = pd.Timestamp(
            shadow_started_at
        )

        if started.tzinfo is None:
            started = started.tz_localize(
                "UTC"
            )
        else:
            started = started.tz_convert(
                "UTC"
            )

        timestamps = pd.to_datetime(
            dataset["timestamp"],
            utc=True,
        )

        prospective = dataset.loc[
            timestamps > started
        ].copy()

        if prospective.empty:
            return {
                "status": (
                    "waiting_for_new_market_data"
                ),
                "observations": 0,
            }

        model = joblib.load(
            self.model_path
        )

        probabilities = (
            model.predict_proba(
                prospective[
                    V38_FEATURE_COLUMNS
                ]
            )
        )

        positions = (
            self._learning_service
            .positions_from_probabilities(
                probabilities=probabilities,
                classes=model.classes_,
                long_threshold=float(
                    metadata[
                        "long_threshold"
                    ]
                ),
                short_threshold=float(
                    metadata[
                        "short_threshold"
                    ]
                ),
            )
        )

        forward_returns = (
            prospective[
                "forward_return"
            ]
            .to_numpy(
                dtype=float
            )
        )

        previous_positions = (
            np.concatenate(
                (
                    np.asarray(
                        [0],
                        dtype=int,
                    ),
                    positions[:-1],
                )
            )
        )

        turnover = np.abs(
            positions
            - previous_positions
        )

        round_trip_cost_bps = float(
            getattr(
                self._learning_service,
                "_round_trip_cost_bps",
            )
        )

        cost_per_turn = (
            round_trip_cost_bps
            / 10_000.0
        )

        net_returns = (
            positions
            * forward_returns
            - turnover
            * cost_per_turn
        )

        trade_count = int(
            np.sum(
                (positions != 0)
                & (
                    positions
                    != previous_positions
                )
            )
        )

        net_return = float(
            np.sum(
                net_returns
            )
        )

        maximum_drawdown = (
            self._calculate_maximum_drawdown(
                net_returns
            )
        )

        observations = int(
            len(
                prospective
            )
        )

        evaluation = {
            "candidate_id": (
                metadata.get(
                    "candidate_id"
                )
            ),
            "timestamp": (
                datetime.now(
                    UTC
                ).isoformat()
            ),
            "first_market_timestamp": str(
                prospective.iloc[
                    0
                ]["timestamp"]
            ),
            "last_market_timestamp": str(
                prospective.iloc[
                    -1
                ]["timestamp"]
            ),
            "observations": observations,
            "trades": trade_count,
            "net_return": net_return,
            "maximum_drawdown": (
                maximum_drawdown
            ),
        }

        self._append_observation(
            evaluation
        )

        metadata[
            "shadow_observations"
        ] = observations

        metadata[
            "shadow_trades"
        ] = trade_count

        metadata[
            "shadow_net_return"
        ] = net_return

        metadata[
            "shadow_maximum_drawdown"
        ] = maximum_drawdown

        metadata[
            "shadow_last_evaluated_at"
        ] = datetime.now(
            UTC
        ).isoformat()

        sufficient_observations = (
            observations
            >= self._minimum_observations
        )

        sufficient_trades = (
            trade_count
            >= self._minimum_trades
        )

        profitable = (
            net_return
            > self._minimum_net_return
        )

        drawdown_acceptable = (
            maximum_drawdown
            <= self._maximum_drawdown_limit
        )

        qualified = (
            sufficient_observations
            and sufficient_trades
            and profitable
            and drawdown_acceptable
        )

        if qualified:
            metadata[
                "shadow_status"
            ] = "qualified"

            self._write_json(
                path=self.metadata_path,
                payload=metadata,
            )

            self._promote(
                metadata=metadata
            )

            metadata[
                "shadow_status"
            ] = "promoted"

            metadata[
                "promoted"
            ] = True

            metadata[
                "promotion_reason"
            ] = (
                "Candidate passed V4.0 "
                "prospective shadow validation."
            )

            status = "promoted"

        else:
            metadata[
                "shadow_status"
            ] = "observing"

            metadata[
                "shadow_gate_status"
            ] = {
                "sufficient_observations": (
                    sufficient_observations
                ),
                "sufficient_trades": (
                    sufficient_trades
                ),
                "profitable": profitable,
                "drawdown_acceptable": (
                    drawdown_acceptable
                ),
            }

            status = "observing"

        self._write_json(
            path=self.metadata_path,
            payload=metadata,
        )

        return {
            "status": status,
            **evaluation,
        }