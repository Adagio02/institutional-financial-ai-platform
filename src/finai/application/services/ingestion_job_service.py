from uuid import UUID

from finai.application.services.market_data_ingestion_service import (
    MarketDataIngestionService,
)
from finai.infrastructure.database.engine import SessionLocal
from finai.infrastructure.database.repositories.ingestion_job_repository import (
    IngestionJobRepository,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)
from finai.infrastructure.market_data.factory import (
    create_market_data_provider,
)


def execute_ingestion_job(
    job_id: UUID,
    provider_name: str,
) -> None:
    session = SessionLocal()

    try:
        job_repository = IngestionJobRepository(session)
        job = job_repository.get_by_id(job_id)

        if job is None:
            return

        job_repository.mark_running(job)

        provider = create_market_data_provider(provider_name)

        ingestion_service = MarketDataIngestionService(
            instrument_repository=InstrumentRepository(session),
            market_bar_repository=MarketBarRepository(session),
            provider=provider,
        )

        result = ingestion_service.ingest(
            symbol=job.symbol,
            interval=job.interval,
            start_time=job.start_time,
            end_time=job.end_time,
        )

        job_repository.mark_completed(
            job,
            received_count=result.received_count,
            inserted_count=result.inserted_count,
        )

    except Exception as exception:
        session.rollback()

        failed_job_repository = IngestionJobRepository(session)
        failed_job = failed_job_repository.get_by_id(job_id)

        if failed_job is not None:
            failed_job_repository.mark_failed(
                failed_job,
                error_message=str(exception),
            )

    finally:
        session.close()
