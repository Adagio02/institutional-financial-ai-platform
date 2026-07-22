from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from finai.api.errors import (
    ApplicationError,
    application_error_handler,
)
from finai.api.middleware.request_id import RequestIDMiddleware
from finai.api.routes.health import router as health_router
from finai.core.config import get_settings
from finai.core.logging import configure_logging
from finai.infrastructure.database.engine import (
    dispose_database_engine,
)


configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    logger.info(
        "application_starting",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_environment,
    )

    yield

    dispose_database_engine()

    logger.info(
        "application_stopped",
        service=settings.app_name,
    )


def create_application() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    application.add_middleware(RequestIDMiddleware)

    application.add_exception_handler(
        ApplicationError,
        application_error_handler,
    )

    application.include_router(health_router)

    return application


app = create_application()