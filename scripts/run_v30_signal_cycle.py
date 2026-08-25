from dataclasses import (
    asdict,
)
import json

from finai.application.services.adaptive_learning_factory import (
    create_adaptive_learning_service,
)
from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    service = (
        create_adaptive_learning_service(
            settings=settings
        )
    )

    signal = service.generate_signal(
        symbol=(
            settings.v30_learning_symbol
        ),
        interval=(
            settings.v30_learning_interval
        ),
    )

    print(
        json.dumps(
            asdict(signal),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()