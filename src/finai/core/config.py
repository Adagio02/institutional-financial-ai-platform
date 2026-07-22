from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Institutional Financial AI Platform"
    app_version: str = "0.2.0"
    app_environment: Literal[
        "development",
        "testing",
        "staging",
        "production",
    ] = "development"

    debug: bool = False
    log_level: str = "INFO"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    database_url: str = Field(
    default="postgresql+psycopg://finai:finai@localhost:5433/finai"
)

    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout_seconds: int = 30
    database_pool_recycle_seconds: int = 1800

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "sec_filings"

    mlflow_tracking_uri: str = "http://localhost:5000"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: SecretStr = SecretStr("minioadmin")

    fred_api_key: SecretStr | None = None
    sec_user_agent: str = "Financial AI Research contact@example.com"
    openai_api_key: SecretStr | None = None

    request_id_header: str = "X-Request-ID"


@lru_cache
def get_settings() -> Settings:
    return Settings()