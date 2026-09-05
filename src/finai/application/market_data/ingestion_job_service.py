import logging
from uuid import UUID

from finai.application.services.market_data_ingestion_service import (
    MarketDataIngestionService,
)
from finai.domain.market_data.enums import BarInterval
from finai.infrastructure.database.engine import SessionLocal
from finai.infrastructure.database.repositories.ingestion_job_repository import (
    IngestionJobRepository,
)
from finai.infrastructure.market_data.factory import (
    create_market_data_provider,
)

from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)


logger = logging.getLogger(__name__)


def execute_ingestion_job(
    job_id: UUID,
    provider_name: str,
) -> None:
    session = SessionLocal()

    try:
        job_repository = IngestionJobRepository(session)
        job = job_repository.get_by_id(job_id)

        if job is None:
            logger.warning(
                "Ingestion job was not found: %s",
                job_id,
            )
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
            interval=BarInterval(job.interval),
            start_time=job.start_time,
            end_time=job.end_time,
        )

        job_repository.mark_completed(
            job,
            received_count=result.bars_received,
            inserted_count=result.bars_persisted,
        )

        logger.info(
            "Ingestion job completed job_id=%s symbol=%s bars=%s",
            job.id,
            job.symbol,
            result.bars_persisted,
        )

    except Exception as error:
        session.rollback()

        logger.exception(
            "Ingestion job failed job_id=%s",
            job_id,
        )

        try:
            job_repository = IngestionJobRepository(session)
            failed_job = job_repository.get_by_id(job_id)

            if failed_job is not None:
                job_repository.mark_failed(
                    failed_job,
                    error_message=str(error),
                )
        except Exception:
            session.rollback()

            logger.exception(
                "Unable to persist failure for job_id=%s",
                job_id,
            )

    finally:
        session.close()
