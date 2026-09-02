from __future__ import annotations

import json

from finai.application.services.v465_learning_factory import (
    build_v465_learning_service,
)
from finai.core.config import get_settings


def main() -> None:
    service = build_v465_learning_service(
        settings=get_settings(),
    )

    result = service.run_locked_validation(
        symbol="AAPL",
        interval="1m",
    )

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
