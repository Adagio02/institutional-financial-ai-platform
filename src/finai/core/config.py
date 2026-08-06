from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://finai:finai@localhost:5433/finai"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "sec_filings"

    model_output_directory: str = "data/models"

    mlflow_experiment_name: str = "institutional-financial-ai-v06"

    training_default_splits: int = 3
    training_default_test_size: int = 10
    training_random_seed: int = 42

    mlflow_tracking_uri: str = "http://localhost:5000"

    fred_api_key: str = ""
    sec_user_agent: str = "InstitutionalFinancialAI research@example.com"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"

    market_data_provider: str = "mock"
    market_data_api_key: str = ""
    market_data_max_bars_per_request: int = 10_000
    market_data_default_query_limit: int = 500
    feature_default_window: int = 20
    feature_max_rows_per_request: int = 100_000

    dataset_output_directory: str = "data/gold/datasets"
    dataset_drop_missing_rows: bool = True

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
