from __future__ import annotations

import json
from dataclasses import (
    asdict,
)

from finai.application.services.v40_learning_factory import (
    create_v40_learning_service,
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
        create_v40_learning_service(
            settings=settings
        )
    )

    result = service.run_learning_cycle(
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
            asdict(
                result
            ),
            indent=2,
            default=str,
        )
    )

    print()

    if result.historical_qualified:
        print(
            "Candidate passed historical "
            "qualification."
        )

        print(
            "V4.0 shadow validation is now "
            "required before champion promotion."
        )

    else:
        print(
            "Candidate did not pass historical "
            "qualification."
        )

        print(
            result.historical_reason
        )


if __name__ == "__main__":
    main()