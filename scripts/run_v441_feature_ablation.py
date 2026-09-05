from __future__ import annotations

import json

from finai.application.services.v441_learning_factory import (
    build_v441_learning_service,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    service = build_v441_learning_service(
        settings=settings,
    )

    result = service.run_feature_ablation(
        symbol="AAPL",
        interval="1m",
        horizon_bars=15,
        edge_bps=3.0,
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
