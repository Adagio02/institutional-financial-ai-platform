from dataclasses import (
    asdict,
)
import json

from finai.application.services.adaptive_learning_factory import (
    create_adaptive_learning_service,
)
from finai.application.services.v30_mlflow_service import (
    V30MlflowService,
)
from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    if not settings.v30_learning_enabled:
        print(
            "V3.0 adaptive learning is disabled."
        )

        return

    service = (
        create_adaptive_learning_service(
            settings=settings
        )
    )

    result = (
        service.run_learning_cycle(
            symbol=(
                settings
                .v30_learning_symbol
            ),
            interval=(
                settings
                .v30_learning_interval
            ),
        )
    )

    logger = V30MlflowService(
        tracking_uri=(
            settings
            .v30_mlflow_tracking_uri
        ),
        experiment_name=(
            settings
            .v30_mlflow_experiment_name
        ),
    )

    logged = logger.log_learning_cycle(
        result=result
    )

    print(
        json.dumps(
            asdict(result),
            indent=2,
        )
    )

    print(
        "MLflow logged:",
        logged,
    )


if __name__ == "__main__":
    main()