from fastapi import FastAPI
from prometheus_client import make_asgi_app
from finai.api.routes import health, market, predictions, risk, portfolio, rag, models, data_quality

app = FastAPI(title="Institutional Financial AI Platform", version="0.1.0")
for router in [
    health.router, market.router, predictions.router, risk.router,
    portfolio.router, rag.router, models.router, data_quality.router
]:
    app.include_router(router)
app.mount("/metrics", make_asgi_app())
