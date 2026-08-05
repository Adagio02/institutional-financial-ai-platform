from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://finai:finai@localhost:5433/finai"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "sec_filings"

    mlflow_tracking_uri: str = "http://localhost:5000"

    fred_api_key: str = ""
    sec_user_agent: str = "InstitutionalFinancialAI research@example.com"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"

    market_data_provider: str = "mock"
    market_data_api_key: str = ""
    market_data_max_bars_per_request: int = 10_000
    market_data_default_query_limit: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
