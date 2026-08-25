import json
from dataclasses import asdict

from finai.application.services.v32_learning_factory import (
    create_v32_learning_service,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    service = create_v32_learning_service(
        settings=settings
    )

    result = service.generate_signal(
        symbol=(
            settings.v32_learning_symbol
        ),
        interval=(
            settings.v32_learning_interval
        ),
    )

    print(
        json.dumps(
            asdict(result),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()