import json
from dataclasses import asdict

from finai.application.services.v33_learning_factory import (
    create_v33_learning_service,
)
from finai.application.services.v33_mlflow_service import (
    V33MlflowService,
)
from finai.core.config import get_settings


def main() -> None:
    settings = get_settings()

    if not settings.v33_learning_enabled:
        print(
            "V3.3 learning is disabled."
        )

        return

    service = (
        create_v33_learning_service(
            settings=settings
        )
    )

    result = service.run_learning_cycle(
        symbol=(
            settings.v33_learning_symbol
        ),
        interval=(
            settings.v33_learning_interval
        ),
    )

    logger = V33MlflowService(
        tracking_uri=(
            settings
            .v33_mlflow_tracking_uri
        ),
        experiment_name=(
            settings
            .v33_mlflow_experiment_name
        ),
    )

    mlflow_logged = (
        logger.log_learning_cycle(
            result=result
        )
    )

    print(
        json.dumps(
            asdict(
                result
            ),
            indent=2,
        )
    )

    print(
        "MLflow logged:",
        mlflow_logged,
    )


if __name__ == "__main__":
    main()