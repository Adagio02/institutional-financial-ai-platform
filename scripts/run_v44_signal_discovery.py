from __future__ import annotations

import json

from finai.application.services.v44_learning_factory import (
    build_v44_learning_service,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    service = build_v44_learning_service(
        settings=settings,
    )

    result = service.run_signal_discovery(
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
