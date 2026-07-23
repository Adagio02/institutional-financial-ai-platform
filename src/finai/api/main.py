from fastapi import FastAPI

from finai.api.routes.health import router as health_router
from finai.api.routes.instruments import router as instruments_router
from finai.api.routes.market_data import router as market_data_router

application = FastAPI(
    title="Institutional Financial AI Platform",
    version="0.3.0",
)

application.include_router(health_router)
application.include_router(instruments_router)
application.include_router(market_data_router)
