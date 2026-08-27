from __future__ import annotations

import json
from dataclasses import (
    asdict,
)

from finai.application.services.v39_learning_factory import (
    create_v39_learning_service,
)
from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    if not settings.v39_learning_enabled:
        print(
            "V3.9 learning is disabled."
        )

        return

    service = (
        create_v39_learning_service(
            settings=settings
        )
    )

    result = (
        service.run_learning_cycle(
            symbol=(
                settings
                .v39_learning_symbol
            ),
            interval=(
                settings
                .v39_learning_interval
            ),
        )
    )

    print()
    print(
        "=== V3.9 REGIME-AWARE "
        "LEARNING RESULT ==="
    )

    print(
        json.dumps(
            asdict(
                result
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()