import json
from dataclasses import asdict

from finai.application.services.v33_learning_factory import (
    create_v33_learning_service,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    service = (
        create_v33_learning_service(
            settings=settings
        )
    )

    signal = service.generate_signal(
        symbol=(
            settings.v33_learning_symbol
        ),
        interval=(
            settings.v33_learning_interval
        ),
    )

    print(
        json.dumps(
            asdict(
                signal
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()