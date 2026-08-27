from __future__ import annotations

import json

from finai.application.services.v40_shadow_factory import (
    create_v40_shadow_service,
)
from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    if not settings.v40_learning_enabled:
        print(
            "V4.0 learning is disabled."
        )

        return

    service = (
        create_v40_shadow_service(
            settings=settings
        )
    )

    result = service.run_cycle(
        symbol=(
            settings
            .v40_learning_symbol
        ),
        interval=(
            settings
            .v40_learning_interval
        ),
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