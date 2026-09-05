import logging
import signal
import sys
from threading import Event

from finai.api.routes.strategy_schedule import (
    build_worker_service,
)
from finai.application.services.strategy_scheduler_daemon import (
    StrategySchedulerDaemon,
)
from finai.application.services.strategy_worker_registry_service import (
    StrategyWorkerRegistryService,
)
from finai.core.config import (
    get_settings,
)
from finai.infrastructure.database.engine import (
    SessionLocal,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s "
        "%(message)s"
    ),
)


def main() -> int:
    settings = get_settings()

    shutdown_event = Event()

    session = SessionLocal()

    worker_service = build_worker_service(
        session=session
    )

    registry_service = (
        StrategyWorkerRegistryService(
            session=session,
            stale_after_seconds=(
                settings
                .strategy_scheduler_worker_stale_seconds
            ),
        )
    )

    daemon = StrategySchedulerDaemon(
        session=session,
        worker_service=worker_service,
        registry_service=registry_service,
        poll_interval_seconds=(
            settings
            .strategy_scheduler_poll_interval_seconds
        ),
        heartbeat_interval_seconds=(
            settings
            .strategy_scheduler_heartbeat_interval_seconds
        ),
        stale_after_seconds=(
            settings
            .strategy_scheduler_worker_stale_seconds
        ),
        shutdown_event=shutdown_event,
    )

    def handle_shutdown(
        signum,
        frame,
    ) -> None:
        del frame

        logging.info(
            "Received shutdown signal %s.",
            signum,
        )

        daemon.request_shutdown()

    signal.signal(
        signal.SIGINT,
        handle_shutdown,
    )

    if hasattr(
        signal,
        "SIGTERM",
    ):
        signal.signal(
            signal.SIGTERM,
            handle_shutdown,
        )

    try:
        daemon.run()

    except KeyboardInterrupt:
        daemon.request_shutdown()

    except Exception:
        logging.exception(
            "Scheduler terminated unexpectedly."
        )

        return 1

    finally:
        session.close()

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )