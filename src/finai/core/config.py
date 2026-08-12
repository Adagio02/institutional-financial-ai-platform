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

    prediction_default_forecast_horizon: str = "next_period"

    governance_minimum_accuracy: float = 0.50
    governance_minimum_r_squared: float = -1.0

    prediction_default_query_limit: int = 100

    backtest_default_initial_capital: float = 100_000.0

    backtest_default_long_threshold: float = 0.60
    backtest_default_short_threshold: float = 0.40

    backtest_default_position_fraction: float = 0.10

    backtest_default_commission_bps: float = 1.0
    backtest_default_slippage_bps: float = 2.0

    backtest_allow_short: bool = False

    risk_periods_per_year: int = 252
    risk_free_rate: float = 0.0

    paper_trading_initial_cash: float = 100_000.0

    paper_trading_commission_bps: float = 1.0
    paper_trading_slippage_bps: float = 2.0

    paper_maximum_order_notional: float = 25_000.0
    paper_maximum_position_notional: float = 50_000.0
    paper_maximum_gross_exposure: float = 100_000.0

    paper_maximum_position_fraction: float = 0.25
    paper_minimum_cash_reserve_fraction: float = 0.05

    paper_quote_maximum_age_seconds: int = 86_400
    paper_quote_interval: str = "1d"

    paper_maximum_daily_loss: float = 5_000.0

    execution_mode: str = "sandbox"

    paper_quote_synthetic_spread_bps: float = 2.0

    sandbox_partial_fill_enabled: bool = True
    sandbox_initial_fill_fraction: float = 0.50

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
