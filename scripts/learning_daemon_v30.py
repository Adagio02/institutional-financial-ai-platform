from __future__ import annotations

from dataclasses import (
    asdict,
)
from datetime import (
    UTC,
    datetime,
)
import json
import time

from finai.application.services.adaptive_learning_factory import (
    create_adaptive_learning_service,
)
from finai.application.services.v30_mlflow_service import (
    V30MlflowService,
)
from finai.core.config import (
    get_settings,
)


def utc_now_seconds() -> float:
    return (
        datetime.now(UTC)
        .timestamp()
    )


def main() -> None:
    settings = get_settings()

    if not settings.v30_learning_enabled:
        raise RuntimeError(
            "V3.0 adaptive learning is disabled."
        )

    service = (
        create_adaptive_learning_service(
            settings=settings
        )
    )

    mlflow_service = (
        V30MlflowService(
            tracking_uri=(
                settings
                .v30_mlflow_tracking_uri
            ),
            experiment_name=(
                settings
                .v30_mlflow_experiment_name
            ),
        )
    )

    next_learning_time = 0.0
    next_signal_time = 0.0

    print(
        "V3.0 learning daemon started."
    )

    print(
        "Symbol:",
        settings.v30_learning_symbol,
    )

    print(
        "Interval:",
        settings.v30_learning_interval,
    )

    print(
        "Retrain seconds:",
        settings
        .v30_learning_retrain_interval_seconds,
    )

    print(
        "Signal seconds:",
        settings
        .v30_signal_interval_seconds,
    )

    while True:
        now = utc_now_seconds()

        if now >= next_learning_time:
            try:
                result = (
                    service
                    .run_learning_cycle(
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

                mlflow_service.log_learning_cycle(
                    result=result
                )

                print(
                    json.dumps(
                        asdict(result),
                        indent=2,
                    )
                )

            except Exception as error:
                print(
                    "Learning cycle failed:",
                    repr(error),
                )

            next_learning_time = (
                now
                + settings
                .v30_learning_retrain_interval_seconds
            )

        if now >= next_signal_time:
            try:
                signal = (
                    service
                    .generate_signal(
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

                print(
                    json.dumps(
                        asdict(signal),
                        indent=2,
                    )
                )

            except Exception as error:
                print(
                    "Signal cycle failed:",
                    repr(error),
                )

            next_signal_time = (
                now
                + settings
                .v30_signal_interval_seconds
            )

        time.sleep(30)


if __name__ == "__main__":
    main()