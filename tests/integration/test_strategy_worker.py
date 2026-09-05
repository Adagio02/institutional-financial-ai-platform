from datetime import UTC, datetime

from fastapi.testclient import TestClient

from finai.api.main import application
from finai.infrastructure.database.engine import (
    SessionLocal,
)
from finai.infrastructure.database.repositories.strategy_worker_repository import (
    StrategyWorkerRepository,
)


client = TestClient(
    application
)


def test_worker_health_endpoint() -> None:
    response = client.get(
        "/api/v1/strategy/workers/health"
    )

    assert response.status_code == 200

    payload = response.json()

    assert "total_workers" in payload
    assert "running_workers" in payload
    assert "stale_workers" in payload
    assert "failed_workers" in payload
    assert "healthy" in payload


def test_worker_can_be_persisted() -> None:
    session = SessionLocal()

    try:
        repository = (
            StrategyWorkerRepository(
                session
            )
        )

        worker = repository.create(
            worker_id=(
                "integration-worker-"
                + datetime.now(UTC)
                .strftime("%Y%m%d%H%M%S%f")
            ),
            hostname="integration-test",
            process_id=12345,
        )

        repository.mark_running(
            worker
        )

        persisted = (
            repository.get_by_id(
                worker.id
            )
        )

        assert persisted is not None
        assert persisted.status == "running"

    finally:
        session.close()