from __future__ import annotations

import json
from dataclasses import (
    asdict,
)

from finai.application.services.v433_learning_factory import (
    create_v41_learning_service,
)
from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    service = create_v41_learning_service(settings=settings)

    result = service.run_learning_cycle(
        symbol=(settings.v41_learning_symbol),
        interval=(settings.v41_learning_interval),
    )

    print()
    print("=== V4.3.1 LEARNING CYCLE ===")

    print(
        json.dumps(
            asdict(result),
            indent=2,
        )
    )

    print()

    if result.promoted:
        print("Unexpected direct promotion.")

    else:
        print("No direct champion promotion.")

    print("Check artifacts/v41/latest_learning_cycle.json for historical/shadow status.")


if __name__ == "__main__":
    main()


