import socket
from uuid import uuid4

from finai.api.routes.strategy_schedule import (
    build_worker_service,
)
from finai.infrastructure.database.engine import (
    SessionLocal,
)


def build_worker_id() -> str:
    hostname = socket.gethostname()

    return (
        f"{hostname}-"
        f"{uuid4().hex[:12]}"
    )


def main() -> None:
    worker_id = build_worker_id()

    session = SessionLocal()

    try:
        service = build_worker_service(
            session=session
        )

        results = service.process_due(
            worker_id=worker_id
        )

        print(
            "Strategy scheduler worker:",
            worker_id,
        )

        print(
            "Schedules processed:",
            len(results),
        )

        for result in results:
            print(
                result.schedule_id,
                result.status,
                result.strategy_run_id,
                result.error_message,
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()