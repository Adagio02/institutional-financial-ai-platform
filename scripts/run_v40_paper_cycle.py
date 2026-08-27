from __future__ import annotations

import json
from pathlib import Path

from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    if settings.v38_live_money_enabled:
        raise RuntimeError(
            "V4.0 refuses live-money execution."
        )

    if settings.execution_mode != "alpaca_paper":
        raise RuntimeError(
            "V4.0 requires alpaca_paper mode."
        )

    champion_directory = Path(
        settings
        .v40_learning_artifact_directory
    )

    champion_path = (
        champion_directory
        / "champion.joblib"
    )

    metadata_path = (
        champion_directory
        / "champion.json"
    )

    if not champion_path.exists():
        print(
            "V4.0 paper cycle blocked safely."
        )

        print(
            "No prospectively validated "
            "V4.0 champion exists."
        )

        return

    if not metadata_path.exists():
        print(
            "V4.0 paper cycle blocked safely."
        )

        print(
            "Champion metadata is missing."
        )

        return

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        metadata,
        dict,
    ):
        raise RuntimeError(
            "V4.0 champion metadata is invalid."
        )

    if not metadata.get(
        "promoted",
        False,
    ):
        print(
            "V4.0 paper cycle blocked safely."
        )

        print(
            "Champion is not marked promoted."
        )

        return

    if (
        metadata.get(
            "shadow_status"
        )
        != "promoted"
    ):
        print(
            "V4.0 paper cycle blocked safely."
        )

        print(
            "Champion has not passed "
            "prospective shadow validation."
        )

        return

    print(
        "V4.0 champion verified."
    )

    print(
        "Paper execution may proceed."
    )

    print(
        "model =",
        champion_path,
    )

    print(
        "candidate_id =",
        metadata.get(
            "candidate_id"
        ),
    )

    print()
    print(
        "Order submission remains disabled "
        "in the V4.0 gate until the existing "
        "paper executor is explicitly wired "
        "to the V4.0 champion."
    )


if __name__ == "__main__":
    main()