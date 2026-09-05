from __future__ import annotations

import json
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Any


class V37RuntimeStateService:
    def __init__(
        self,
        *,
        state_path: str,
        event_log_path: str,
    ) -> None:
        self._state_path = Path(
            state_path
        )

        self._event_log_path = Path(
            event_log_path
        )

        self._state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._event_log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def load(
        self,
    ) -> dict[str, Any]:
        if not self._state_path.exists():
            return {
                "version": "3.7",
                "last_learning_bar_count": 0,
                "last_learning_timestamp": None,
                "jobs": {},
            }

        raw = self._state_path.read_text(
            encoding="utf-8"
        )

        payload = json.loads(
            raw
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                "V3.7 runtime state is invalid."
            )

        return payload

    def save(
        self,
        state: dict[str, Any],
    ) -> None:
        temporary_path = (
            self._state_path
            .with_suffix(
                ".tmp"
            )
        )

        temporary_path.write_text(
            json.dumps(
                state,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(
            self._state_path
        )

    def record_event(
        self,
        *,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "timestamp": (
                datetime.now(UTC)
                .isoformat()
            ),
            "event_type": (
                event_type
            ),
            "message": message,
            "details": (
                details
                if details is not None
                else {}
            ),
        }

        with self._event_log_path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    payload,
                    sort_keys=True,
                )
            )

            handle.write(
                "\n"
            )

    @staticmethod
    def utc_now_string() -> str:
        return (
            datetime.now(UTC)
            .isoformat()
        )