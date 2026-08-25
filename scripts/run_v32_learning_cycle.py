import json
from dataclasses import asdict

from finai.application.services.v32_learning_factory import (
    create_v32_learning_service,
)
from finai.application.services.v32_mlflow_service import (
    V32MlflowService,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    if not settings.v32_learning_enabled:
        print(
            "V3.2 learning is disabled."
        )

        return

    service = create_v32_learning_service(
        settings=settings
    )

    result = service.run_learning_cycle(
        symbol=(
            settings.v32_learning_symbol
        ),
        interval=(
            settings.v32_learning_interval
        ),
    )

    logger = V32MlflowService(
        tracking_uri=(
            settings
            .v32_mlflow_tracking_uri
        ),
        experiment_name=(
            settings
            .v32_mlflow_experiment_name
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