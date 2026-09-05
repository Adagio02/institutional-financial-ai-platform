from __future__ import annotations

from finai.application.services.v47_bulk_ingestion_service import (
    V47BulkIngestionService,
)
from finai.core.config import Settings
from finai.infrastructure.market_data.v47_alpaca_provider import (
    V47AlpacaHistoricalProvider,
)


def _optional_setting(
    settings: Settings,
    names: tuple[str, ...],
    default,
):
    for name in names:
        if hasattr(
            settings,
            name,
        ):
            value = getattr(
                settings,
                name,
            )
            if value is not None:
                return value
    return default


def build_v47_bulk_ingestion_service(
    *,
    settings: Settings,
) -> V47BulkIngestionService:
    provider = V47AlpacaHistoricalProvider(
        api_key=settings.alpaca_api_key,
        secret_key=(
            settings.alpaca_secret_key
        ),
        feed=str(
            _optional_setting(
                settings,
                (
                    "alpaca_market_data_feed",
                    "market_data_alpaca_feed",
                    "alpaca_feed",
                ),
                "iex",
            )
        ),
        timeout_seconds=float(
            _optional_setting(
                settings,
                (
                    "alpaca_request_timeout_seconds",
                    "market_data_timeout_seconds",
                ),
                15.0,
            )
        ),
        request_limit=10_000,
    )

    return V47BulkIngestionService(
        database_url=settings.database_url,
        provider=provider,
        universe_path=(
            "config/v47_universe.json"
        ),
        artifact_directory=(
            "artifacts/v47/ingestion"
        ),
        maximum_bars_per_window=(
            10_000
        ),
        request_delay_seconds=0.40,
        retry_count=5,
    )
