from __future__ import annotations

import json
import shutil
from dataclasses import (
    asdict,
    dataclass,
)
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Any

from finai.application.services.v38_learning_service import (
    V38LearningCycleResult,
)
from finai.application.services.v39_learning_service import (
    V39LearningService,
)


@dataclass(
    frozen=True,
    slots=True,
)
class V40LearningCycleResult:
    symbol: str
    interval: str
    winning_model: str

    candidate_path: str
    candidate_metadata_path: str
    candidate_composite_score: float

    historical_qualified: bool
    historical_reason: str

    shadow_candidate_path: str | None
    shadow_metadata_path: str | None

    champion_path: str | None
    shadow_required: bool

    completed_at: str


class V40LearningService(
    V39LearningService
):
    VERSION = "4.0"

    LEARNING_ARCHITECTURE = (
        "regime_aware_prospective_shadow_governance"
    )

    def __init__(
        self,
        *,
        shadow_directory: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **kwargs
        )

        self._shadow_directory = Path(
            shadow_directory
        )

        self._shadow_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @property
    def shadow_candidate_path(
        self,
    ) -> Path:
        return (
            self._shadow_directory
            / "shadow_candidate.joblib"
        )

    @property
    def shadow_metadata_path(
        self,
    ) -> Path:
        return (
            self._shadow_directory
            / "shadow_candidate.json"
        )

    @property
    def shadow_history_path(
        self,
    ) -> Path:
        return (
            self._shadow_directory
            / "shadow_history.jsonl"
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
                f"Expected JSON object: {path}"
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

    @staticmethod
    def _append_jsonl(
        *,
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
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

    def _remove_premature_champion(
        self,
        *,
        result: V38LearningCycleResult,
        candidate_path: Path,
        candidate_metadata_path: Path,
    ) -> None:
        if not result.promoted:
            return

        if self.champion_path.exists():
            try:
                if (
                    self.champion_path.read_bytes()
                    == candidate_path.read_bytes()
                ):
                    self.champion_path.unlink()
            except OSError:
                pass

        if self.champion_metadata_path.exists():
            try:
                champion_metadata = (
                    self._load_json(
                        self.champion_metadata_path
                    )
                )

                candidate_metadata = (
                    self._load_json(
                        candidate_metadata_path
                    )
                )

                if (
                    champion_metadata.get(
                        "created_at"
                    )
                    == candidate_metadata.get(
                        "created_at"
                    )
                ):
                    self.champion_metadata_path.unlink()

            except (
                OSError,
                RuntimeError,
                json.JSONDecodeError,
            ):
                pass

    def _patch_candidate_metadata(
        self,
        *,
        path: Path,
        historical_qualified: bool,
        historical_reason: str,
    ) -> dict[str, Any]:
        payload = self._load_json(
            path
        )

        payload["version"] = self.VERSION

        payload[
            "learning_architecture"
        ] = self.LEARNING_ARCHITECTURE

        payload[
            "historical_qualified"
        ] = historical_qualified

        payload[
            "historical_reason"
        ] = historical_reason

        payload[
            "shadow_validation_required"
        ] = True

        payload[
            "shadow_status"
        ] = (
            "pending"
            if historical_qualified
            else "not_eligible"
        )

        payload["promoted"] = False

        payload[
            "promotion_reason"
        ] = (
            "Awaiting prospective V4.0 "
            "shadow validation."
            if historical_qualified
            else historical_reason
        )

        payload[
            "v40_updated_at"
        ] = datetime.now(
            UTC
        ).isoformat()

        self._write_json(
            path=path,
            payload=payload,
        )

        return payload

    def _stage_shadow_candidate(
        self,
        *,
        candidate_path: Path,
        candidate_metadata_path: Path,
        historical_reason: str,
    ) -> tuple[
        Path,
        Path,
    ]:
        metadata = self._load_json(
            candidate_metadata_path
        )

        candidate_id = candidate_path.stem

        staged_at = datetime.now(
            UTC
        ).isoformat()

        shutil.copyfile(
            candidate_path,
            self.shadow_candidate_path,
        )

        shadow_metadata = dict(
            metadata
        )

        shadow_metadata.update(
            {
                "version": self.VERSION,
                "candidate_id": candidate_id,
                "source_candidate_path": str(
                    candidate_path
                ),
                "model_path": str(
                    self.shadow_candidate_path
                ),
                "historical_qualified": True,
                "historical_reason": (
                    historical_reason
                ),
                "shadow_validation_required": True,
                "shadow_status": "active",
                "shadow_started_at": staged_at,
                "shadow_observations": 0,
                "shadow_trades": 0,
                "shadow_net_return": 0.0,
                "shadow_maximum_drawdown": 0.0,
                "promoted": False,
                "promotion_reason": (
                    "Awaiting prospective V4.0 "
                    "shadow validation."
                ),
            }
        )

        self._write_json(
            path=self.shadow_metadata_path,
            payload=shadow_metadata,
        )

        self._append_jsonl(
            path=self.shadow_history_path,
            payload={
                "event": "shadow_candidate_staged",
                "candidate_id": candidate_id,
                "candidate_path": str(
                    candidate_path
                ),
                "shadow_candidate_path": str(
                    self.shadow_candidate_path
                ),
                "timestamp": staged_at,
            },
        )

        return (
            self.shadow_candidate_path,
            self.shadow_metadata_path,
        )

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V40LearningCycleResult:
        base_result = (
            super()
            .run_learning_cycle(
                symbol=symbol,
                interval=interval,
            )
        )

        candidate_path = Path(
            base_result.candidate_path
        )

        candidate_metadata_path = Path(
            base_result
            .candidate_metadata_path
        )

        if not candidate_path.exists():
            raise FileNotFoundError(
                f"Candidate missing: "
                f"{candidate_path}"
            )

        if not candidate_metadata_path.exists():
            raise FileNotFoundError(
                "Candidate metadata missing: "
                f"{candidate_metadata_path}"
            )

        historical_qualified = bool(
            base_result.promoted
        )

        historical_reason = (
            base_result.promotion_reason
        )

        self._remove_premature_champion(
            result=base_result,
            candidate_path=candidate_path,
            candidate_metadata_path=(
                candidate_metadata_path
            ),
        )

        self._patch_candidate_metadata(
            path=candidate_metadata_path,
            historical_qualified=(
                historical_qualified
            ),
            historical_reason=(
                historical_reason
            ),
        )

        shadow_candidate_path = None
        shadow_metadata_path = None

        if historical_qualified:
            (
                staged_model,
                staged_metadata,
            ) = self._stage_shadow_candidate(
                candidate_path=candidate_path,
                candidate_metadata_path=(
                    candidate_metadata_path
                ),
                historical_reason=(
                    historical_reason
                ),
            )

            shadow_candidate_path = str(
                staged_model
            )

            shadow_metadata_path = str(
                staged_metadata
            )

        completed_at = datetime.now(
            UTC
        ).isoformat()

        result = V40LearningCycleResult(
            symbol=base_result.symbol,
            interval=base_result.interval,
            winning_model=(
                base_result.winning_model
            ),
            candidate_path=str(
                candidate_path
            ),
            candidate_metadata_path=str(
                candidate_metadata_path
            ),
            candidate_composite_score=(
                base_result
                .candidate_composite_score
            ),
            historical_qualified=(
                historical_qualified
            ),
            historical_reason=(
                historical_reason
            ),
            shadow_candidate_path=(
                shadow_candidate_path
            ),
            shadow_metadata_path=(
                shadow_metadata_path
            ),
            champion_path=None,
            shadow_required=True,
            completed_at=completed_at,
        )

        self._write_json(
            path=(
                self._artifact_directory
                / "latest_learning_cycle.json"
            ),
            payload=asdict(result),
        )

        self._append_jsonl(
            path=(
                self._shadow_directory
                / "learning_history.jsonl"
            ),
            payload={
                **asdict(result),
                "event": "v40_learning_cycle",
            },
        )

        return result