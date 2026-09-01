from __future__ import annotations

import json

from finai.application.services.v443_learning_factory import (
    build_v443_learning_service,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    service = build_v443_learning_service(
        settings=settings,
    )

    frozen = service.freeze_best_candidate()

    print(
        json.dumps(
            frozen,
            indent=2,
            default=str,
        )
    )

    if frozen.get("frozen"):
        locked = service.run_locked_validation(
            symbol="AAPL",
            interval="1m",
        )

        print(
            json.dumps(
                locked,
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    main()
