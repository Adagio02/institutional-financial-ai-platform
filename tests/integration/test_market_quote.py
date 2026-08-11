from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application
from finai.application.services.market_quote_service import (
    MarketQuoteService,
)
from finai.infrastructure.database.engine import (
    SessionLocal,
)


client = TestClient(application)


def test_quote_uses_latest_persisted_market_bar() -> None:
    symbol = f"Q{uuid4().hex[:7]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Quote Test Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201

    ingestion_response = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": "2026-07-01T00:00:00Z",
            "end_time": "2026-07-10T00:00:00Z",
        },
    )

    assert ingestion_response.status_code == 201

    session = SessionLocal()

    try:
        service = MarketQuoteService(
            session=session,
            maximum_quote_age_seconds=(
                60 * 60 * 24 * 365
            ),
        )

        quote = service.get_quote(
            symbol=symbol
        )

        assert quote.symbol == symbol
        assert quote.price > 0
        assert quote.timestamp is not None
        assert quote.provider

    finally:
        session.close()