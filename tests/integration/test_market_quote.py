from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import uuid4

from fastapi.testclient import (
    TestClient,
)

from finai.api.main import application
from finai.application.services.market_quote_service import (
    MarketQuoteService,
)
from finai.domain.market_data.enums import (
    BarInterval,
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

    assert instrument_response.status_code == 201, instrument_response.text

    end_time = datetime.now(UTC)

    start_time = end_time - timedelta(days=5)

    ingestion_response = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": (start_time.isoformat()),
            "end_time": (end_time.isoformat()),
        },
    )

    assert ingestion_response.status_code == 201, ingestion_response.text

    session = SessionLocal()

    try:
        service = MarketQuoteService(
            session=session,
            maximum_quote_age_seconds=(60 * 60 * 24 * 7),
            quote_interval=(BarInterval.ONE_DAY),
            synthetic_spread_bps=2.0,
        )

        quote = service.get_quote(symbol=symbol)

        assert quote.symbol == symbol

        assert quote.bid > 0
        assert quote.ask > 0
        assert quote.last > 0

        assert quote.ask >= quote.bid

        assert quote.bid < quote.last

        assert quote.ask > quote.last

        assert quote.midpoint > 0

        assert quote.timestamp is not None

        assert quote.provider

    finally:
        session.close()


def test_quote_midpoint_matches_bid_and_ask() -> None:
    symbol = f"M{uuid4().hex[:7]}".upper()

    instrument_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": ("Midpoint Quote Test Instrument"),
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert instrument_response.status_code == 201, instrument_response.text

    end_time = datetime.now(UTC)

    start_time = end_time - timedelta(days=5)

    ingestion_response = client.post(
        "/api/v1/market-data/ingest",
        json={
            "symbol": symbol,
            "interval": "1d",
            "start_time": (start_time.isoformat()),
            "end_time": (end_time.isoformat()),
        },
    )

    assert ingestion_response.status_code == 201, ingestion_response.text

    session = SessionLocal()

    try:
        service = MarketQuoteService(
            session=session,
            maximum_quote_age_seconds=(60 * 60 * 24 * 7),
            quote_interval=(BarInterval.ONE_DAY),
            synthetic_spread_bps=2.0,
        )

        quote = service.get_quote(symbol=symbol)

        expected_midpoint = (quote.bid + quote.ask) / 2.0

        assert quote.midpoint == expected_midpoint

    finally:
        session.close()
