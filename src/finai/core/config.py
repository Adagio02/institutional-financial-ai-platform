from functools import lru_cache

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    # ---------------------------------------------------------
    # Application
    # ---------------------------------------------------------

    app_env: str = "development"

    log_level: str = "INFO"

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    database_url: str = "postgresql+psycopg://finai:finai@localhost:5433/finai"

    # ---------------------------------------------------------
    # Vector database / retrieval
    # ---------------------------------------------------------

    qdrant_url: str = "http://localhost:6333"

    qdrant_collection: str = "sec_filings"

    # ---------------------------------------------------------
    # MLflow
    # ---------------------------------------------------------

    mlflow_tracking_uri: str = "http://localhost:5000"

    mlflow_experiment_name: str = "institutional-financial-ai"

    # ---------------------------------------------------------
    # Model governance
    # ---------------------------------------------------------

    governance_minimum_accuracy: float = 0.50

    governance_minimum_r_squared: float = 0.00
    # ---------------------------------------------------------
    # External APIs
    # ---------------------------------------------------------

    fred_api_key: str = ""

    sec_user_agent: str = "InstitutionalFinancialAI research@example.com"

    openai_api_key: str = ""

    openai_chat_model: str = "gpt-4.1-mini"

    # ---------------------------------------------------------
    # Market data
    # ---------------------------------------------------------

    market_data_provider: str = "mock"

    market_data_api_key: str = ""

    market_data_max_bars_per_request: int = 10_000

    market_data_default_query_limit: int = 500

    # ---------------------------------------------------------
    # Dataset construction
    # ---------------------------------------------------------

    dataset_output_directory: str = "artifacts/datasets"

    # ---------------------------------------------------------
    # Model artifacts
    # ---------------------------------------------------------

    model_output_directory: str = "artifacts/models"

    # ---------------------------------------------------------
    # Paper trading
    # ---------------------------------------------------------

    paper_trading_initial_cash: float = 100_000.0

    paper_trading_commission_bps: float = 1.0

    paper_trading_slippage_bps: float = 2.0

    # ---------------------------------------------------------
    # Paper-trading risk limits
    # ---------------------------------------------------------

    paper_maximum_order_notional: float = 25_000.0

    paper_maximum_position_notional: float = 50_000.0

    paper_maximum_gross_exposure: float = 100_000.0

    paper_maximum_position_fraction: float = 0.25

    paper_minimum_cash_reserve_fraction: float = 0.05

    paper_maximum_daily_loss: float = 5_000.0

    # ---------------------------------------------------------
    # Market quote configuration
    # ---------------------------------------------------------

    paper_quote_maximum_age_seconds: int = 86_400

    paper_quote_interval: str = "1d"

    paper_quote_synthetic_spread_bps: float = 2.0

    # ---------------------------------------------------------
    # Execution
    # ---------------------------------------------------------

    execution_mode: str = "sandbox"

    sandbox_partial_fill_enabled: bool = True

    sandbox_initial_fill_fraction: float = 0.50

    # ---------------------------------------------------------
    # Version 1.2 strategy orchestration
    # ---------------------------------------------------------

    strategy_minimum_confidence: float = 0.60

    strategy_maximum_buy_equity_fraction: float = 0.05

    strategy_maximum_sell_position_fraction: float = 1.0

    strategy_minimum_order_notional: float = 100.0

    strategy_proposal_maximum_age_seconds: int = 900

    strategy_maximum_price_drift_bps: float = 100.0

    strategy_manual_approval_required: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
