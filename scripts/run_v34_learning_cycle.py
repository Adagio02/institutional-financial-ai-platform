import json
from dataclasses import asdict

from finai.application.services.v34_learning_factory import (
    create_v34_learning_service,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    if not settings.v34_learning_enabled:
        print(
            "V3.4 learning is disabled."
        )

        return

    service = (
        create_v34_learning_service(
            settings=settings
        )
    )

    result = service.run_learning_cycle(
        symbol=(
            settings.v34_learning_symbol
        ),
        interval=(
            settings.v34_learning_interval
        ),
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