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
    # ---------------------------------------------------------
    # Version 1.3 strategy governance
    # ---------------------------------------------------------

    strategy_default_capital_budget_fraction: float = 0.25

    strategy_default_maximum_single_proposal_fraction: float = 0.25

    strategy_default_maximum_gross_exposure_fraction: float = 1.0

    strategy_default_maximum_symbol_fraction: float = 0.50

    strategy_default_maximum_daily_loss: float = 1_000.0

    strategy_default_cooldown_seconds: int = 300

    strategy_default_maximum_active_proposals: int = 5

    strategy_competing_signal_resolution_enabled: bool = True

    # ---------------------------------------------------------
    # Version 1.4 strategy runs
    # ---------------------------------------------------------

    strategy_run_maximum_signals: int = 25

        # Version 1.5 strategy schedules
    strategy_schedule_maximum_per_account: int = 20

        # Version 1.6 scheduler worker
    strategy_schedule_lease_seconds: int = 300

    strategy_schedule_worker_batch_size: int = 20

    strategy_schedule_retry_base_seconds: int = 60

    strategy_schedule_retry_maximum_seconds: int = 3600

    strategy_schedule_maximum_failures: int = 5

        # Version 1.7 scheduler daemon
    strategy_scheduler_poll_interval_seconds: int = 10

    strategy_scheduler_heartbeat_interval_seconds: int = 15

    strategy_scheduler_worker_stale_seconds: int = 60

        # Version 1.8 trading controls
    trading_control_maximum_daily_loss_fraction: float = 0.05

    trading_control_maximum_gross_exposure_fraction: float = 1.50

    trading_control_maximum_symbol_fraction: float = 0.25

    trading_control_maximum_order_fraction: float = 0.10

        # Version 1.9 Alpaca paper broker
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    alpaca_request_timeout_seconds: float = 15.0

    alpaca_paper_trading_enabled: bool = False

        # Version 2.0 external paper execution
    alpaca_execution_enabled: bool = False

    alpaca_execution_commission_bps: float = 0.0

    alpaca_sync_on_submit: bool = True

    alpaca_maximum_sync_orders: int = 100

        # Version 2.1 Alpaca trade-update stream
    alpaca_trade_stream_enabled: bool = False

    alpaca_trade_stream_url: str = (
        "wss://paper-api.alpaca.markets/stream"
    )

    alpaca_trade_stream_open_timeout_seconds: float = 10.0

    alpaca_trade_stream_reconnect_initial_seconds: float = 2.0

    alpaca_trade_stream_reconnect_maximum_seconds: float = 30.0

        # Version 2.2 Alpaca reconciliation
    alpaca_reconciliation_enabled: bool = False

    alpaca_reconciliation_interval_seconds: int = 60

    alpaca_reconciliation_batch_size: int = 100

    alpaca_reconciliation_initial_backoff_seconds: float = 2.0

    alpaca_reconciliation_maximum_backoff_seconds: float = 30.0

        # Version 2.3 Alpaca broker discovery
    alpaca_order_discovery_enabled: bool = False

    alpaca_order_discovery_interval_seconds: int = 300

    alpaca_order_discovery_limit: int = 500

    alpaca_order_discovery_direction: str = "desc"

        # Version 2.4 safe Alpaca orphan recovery
    alpaca_orphan_recovery_enabled: bool = False

    alpaca_orphan_recovery_require_symbol_match: bool = True

    alpaca_orphan_recovery_require_quantity_match: bool = True

        # Version 2.5 Alpaca account preflight guard
    alpaca_account_guard_enabled: bool = True

    alpaca_account_guard_require_active: bool = True

    alpaca_account_guard_maximum_buying_power_fraction: float = 0.10

    alpaca_account_guard_require_positive_buying_power: bool = True

        # Version 2.6 Alpaca asset and session guard
    alpaca_market_guard_enabled: bool = True

    alpaca_market_guard_require_active_asset: bool = True

    alpaca_market_guard_require_tradable_asset: bool = True

    alpaca_market_guard_require_market_open: bool = True

    alpaca_market_guard_require_fractionable: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
