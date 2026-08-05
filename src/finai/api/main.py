from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from finai.api.exception_handlers import (
    register_exception_handlers,
)
from finai.api.routes.health import router as health_router
from finai.api.routes.ingestion_job import (
    router as ingestion_job_router,
)
from finai.api.routes.instruments import (
    router as instruments_router,
)
from finai.api.routes.market_data import (
    router as market_data_router,
)
from finai.api.routes.dataset import (
    router as dataset_router,
)
from finai.api.routes.feature import (
    router as feature_router,
)


application = FastAPI(
    title="Institutional Financial AI Platform",
    version="0.4.0",
)

application.include_router(health_router)
application.include_router(instruments_router)
application.include_router(market_data_router)
application.include_router(ingestion_job_router)
application.include_router(feature_router)
application.include_router(dataset_router)

register_exception_handlers(application)

Instrumentator().instrument(application).expose(
    application,
    endpoint="/metrics",
    include_in_schema=False,
)
