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
from finai.api.routes.model import (
    router as model_router,
)
from finai.api.routes.training import (
    router as training_router,
)
from finai.api.routes.explanation import (
    router as explanation_router,
)
from finai.api.routes.model_governance import (
    router as model_governance_router,
)
from finai.api.routes.prediction import (
    router as prediction_router,
)
from finai.api.routes.backtest import (
    router as backtest_router,
)
from finai.api.routes.risk import (
    router as risk_router,
)
from finai.api.routes.order import (
    router as order_router,
)
from finai.api.routes.paper_account import (
    router as paper_account_router,
)
from finai.api.routes.portfolio import (
    router as portfolio_router,
)
from finai.api.routes.reconciliation import (
    router as reconciliation_router,
)
from finai.api.routes.trading_control import (
    router as trading_control_router,
)
from finai.api.routes.execution_audit import (
    router as execution_audit_router,
)
from finai.api.routes.execution import (
    router as execution_router,
)
from finai.api.routes.strategy import (
    router as strategy_router,
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
application.include_router(training_router)
application.include_router(model_router)
application.include_router(prediction_router)
application.include_router(explanation_router)
application.include_router(model_governance_router)
application.include_router(backtest_router)
application.include_router(risk_router)
application.include_router(paper_account_router)
application.include_router(order_router)
application.include_router(portfolio_router)
application.include_router(trading_control_router)

application.include_router(reconciliation_router)
application.include_router(execution_audit_router)
application.include_router(execution_router)
application.include_router(strategy_router)

register_exception_handlers(application)

Instrumentator().instrument(application).expose(
    application,
    endpoint="/metrics",
    include_in_schema=False,
)
