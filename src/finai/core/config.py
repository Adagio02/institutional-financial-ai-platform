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

        # Version 2.7 Alpaca idempotent submission
    alpaca_idempotency_guard_enabled: bool = True

    alpaca_idempotency_lookup_before_submit: bool = True

    alpaca_idempotency_recover_after_transport_error: bool = True

    alpaca_idempotency_require_order_match: bool = True

        # Version 2.8 Alpaca live quote integrity guard
    alpaca_data_base_url: str = (
        "https://data.alpaca.markets"
    )

    alpaca_market_data_feed: str = "iex"

    alpaca_quote_guard_enabled: bool = True

    alpaca_quote_guard_maximum_age_seconds: int = 60

    alpaca_quote_guard_maximum_spread_bps: float = 100.0

    alpaca_quote_guard_maximum_reference_deviation_bps: float = 250.0

    pre_trade_risk_enabled: bool = True

    pre_trade_maximum_order_quantity: float = 100.0

    pre_trade_maximum_order_notional: float = 25_000.0

    pre_trade_maximum_position_notional: float = 50_000.0

    pre_trade_maximum_buying_power_fraction: float = 0.10

        # Version 3.0 adaptive learning
    v30_learning_enabled: bool = True

    v30_learning_symbol: str = "AAPL"

    v30_learning_interval: str = "1m"

    v30_learning_minimum_rows: int = 500

    v30_learning_validation_fraction: float = 0.20

    v30_learning_minimum_score: float = 0.50

    v30_learning_minimum_promotion_improvement: float = 0.01

    v30_learning_retrain_interval_seconds: int = 21_600

    v30_signal_interval_seconds: int = 300

    v30_signal_probability_threshold: float = 0.55

    v30_learning_artifact_directory: str = (
        "artifacts/v30"
    )

    v30_learning_require_non_mock_data: bool = True

    v30_mlflow_tracking_uri: str = (
        "http://127.0.0.1:5000"
    )

    v30_mlflow_experiment_name: str = (
        "finai-v30-adaptive-learning"
    )

        # Version 3.1 walk-forward,
    # cost-aware adaptive learning
    v31_learning_enabled: bool = True

    v31_learning_symbol: str = "AAPL"
    v31_learning_interval: str = "1m"

    v31_learning_artifact_directory: str = (
        "artifacts/v31"
    )

    v31_learning_minimum_rows: int = 2_000

    v31_forward_horizon_bars: int = 5

    v31_target_minimum_edge_bps: float = 8.0

    v31_round_trip_cost_bps: float = 4.0

    v31_walk_forward_folds: int = 5

    v31_minimum_balanced_accuracy: float = 0.34

    v31_minimum_macro_f1: float = 0.30

    v31_minimum_net_return: float = 0.0

    v31_minimum_trades: int = 20

    v31_minimum_promotion_improvement: float = 0.0025

    v31_signal_probability_threshold: float = 0.55

    v31_learning_require_non_mock_data: bool = True

    v31_mlflow_tracking_uri: str = (
        "http://127.0.0.1:5000"
    )

    v31_mlflow_experiment_name: str = (
        "finai-v31-walk-forward-learning"
    )

        # Version 3.2 research-grade adaptive learning
    v32_learning_enabled: bool = True

    v32_learning_symbol: str = "AAPL"
    v32_learning_interval: str = "1m"

    v32_learning_artifact_directory: str = (
        "artifacts/v32"
    )

    v32_learning_minimum_rows: int = 4_000

    v32_forward_horizon_bars: int = 5

    v32_target_minimum_edge_bps: float = 8.0

    v32_round_trip_cost_bps: float = 4.0

    v32_walk_forward_folds: int = 5

    v32_holdout_fraction: float = 0.20

    v32_signal_probability_threshold: float = 0.60

    v32_minimum_balanced_accuracy: float = 0.34

    v32_minimum_macro_f1: float = 0.30

    v32_minimum_net_return: float = 0.0

    v32_minimum_trades: int = 20

    v32_maximum_drawdown: float = 0.10

    v32_minimum_sharpe_like: float = 0.0

    v32_minimum_fold_positive_fraction: float = 0.60

    v32_minimum_baseline_improvement: float = 0.0025

    v32_minimum_promotion_improvement: float = 0.005

    v32_learning_require_non_mock_data: bool = True

    v32_mlflow_tracking_uri: str = (
        "http://127.0.0.1:5000"
    )

    v32_mlflow_experiment_name: str = (
        "finai-v32-research-grade-learning"
    )

        # Version 3.3 profit-aware champion search
    v33_learning_enabled: bool = True

    v33_learning_symbol: str = "AAPL"
    v33_learning_interval: str = "1m"

    v33_learning_artifact_directory: str = (
        "artifacts/v33"
    )

    v33_learning_minimum_rows: int = 10_000

    v33_holdout_fraction: float = 0.20

    v33_forward_horizon_bars: int = 5

    v33_target_volatility_multiplier: float = 0.35

    v33_round_trip_cost_bps: float = 4.0

    v33_walk_forward_folds: int = 5

    v33_purge_bars: int = 10

    v33_long_probability_thresholds: str = (
        "0.34,0.36,0.38,0.40,0.42,"
        "0.44,0.46,0.48,0.50,0.525,"
        "0.55,0.575,0.60"
    )

    v33_short_probability_thresholds: str = (
        "0.34,0.36,0.38,0.40,0.42,"
        "0.44,0.46,0.48,0.50,0.525,"
        "0.55,0.575,0.60"
    )

    v33_minimum_balanced_accuracy: float = 0.34

    v33_minimum_macro_f1: float = 0.28

    v33_minimum_net_return: float = 0.0

    v33_minimum_trades: int = 20

    v33_maximum_drawdown: float = 0.10

    v33_minimum_positive_fold_fraction: float = 0.60

    v33_minimum_baseline_improvement: float = 0.0

    v33_minimum_promotion_improvement: float = 0.005

    v33_learning_require_non_mock_data: bool = True

    v33_mlflow_tracking_uri: str = (
        "http://127.0.0.1:5000"
    )

    v33_mlflow_experiment_name: str = (
        "finai-v33-profit-aware-learning"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
