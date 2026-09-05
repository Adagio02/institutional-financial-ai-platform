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

    # Version 3.4 real-world regime-aware learning
    v34_learning_enabled: bool = True

    v34_learning_symbol: str = "AAPL"
    v34_learning_interval: str = "1m"

    v34_learning_artifact_directory: str = (
        "artifacts/v34"
    )

    v34_learning_minimum_rows: int = 20_000

    v34_holdout_fraction: float = 0.20

    v34_forward_horizon_bars: int = 5

    v34_target_volatility_multiplier: float = 0.35

    v34_round_trip_cost_bps: float = 4.0

    v34_walk_forward_folds: int = 5

    v34_purge_bars: int = 10

    v34_inner_calibration_fraction: float = 0.20

    v34_long_probability_thresholds: str = (
        "0.34,0.36,0.38,0.40,0.42,"
        "0.44,0.46,0.48,0.50,0.525,"
        "0.55,0.575,0.60"
    )

    v34_short_probability_thresholds: str = (
        "0.34,0.36,0.38,0.40,0.42,"
        "0.44,0.46,0.48,0.50,0.525,"
        "0.55,0.575,0.60"
    )

    v34_threshold_search_minimum_trades: int = 5

    v34_minimum_balanced_accuracy: float = 0.34

    v34_minimum_macro_f1: float = 0.28

    v34_minimum_net_return: float = 0.0

    v34_minimum_trades: int = 20

    v34_maximum_drawdown: float = 0.15

    v34_minimum_positive_fold_fraction: float = 0.60

    v34_minimum_worst_fold_return: float = -0.05

    v34_maximum_threshold_std: float = 0.10

    v34_minimum_regime_return: float = -0.05

    v34_minimum_baseline_improvement: float = 0.0

    v34_minimum_promotion_improvement: float = 0.005

    v34_learning_require_non_mock_data: bool = True

    v34_mlflow_tracking_uri: str = (
        "http://127.0.0.1:5000"
    )

    v34_mlflow_experiment_name: str = (
        "finai-v34-real-world-learning"
    )

    # Real-data daemon
    v34_ingestion_refresh_seconds: int = 300

    v34_ingestion_lookback_days: int = 5

    v34_learning_refresh_seconds: int = 21_600

    v34_learning_minimum_new_bars: int = 250

        # Version 3.5 live inference and shadow trading
    v35_inference_enabled: bool = True

    v35_inference_symbol: str = "AAPL"

    v35_inference_interval: str = "1m"

    v35_artifact_directory: str = (
        "artifacts/v35"
    )

    v35_champion_directory: str = (
        "artifacts/v34"
    )

    v35_minimum_confidence: float = 0.55

    v35_shadow_trading_enabled: bool = True

    v35_broker_submission_enabled: bool = False

    v35_prediction_log_path: str = (
        "artifacts/v35/predictions.jsonl"
    )

    v35_signal_log_path: str = (
        "artifacts/v35/shadow_signals.jsonl"
    )

    v35_maximum_feature_age_seconds: int = 180

    v35_require_alpaca_data: bool = True

        # Version 3.6 continuous paper execution
    v36_execution_enabled: bool = True

    # Must remain paper-only for V3.6.
    v36_live_money_enabled: bool = False

    v36_symbol: str = "AAPL"
    v36_interval: str = "1m"

    v36_artifact_directory: str = (
        "artifacts/v36"
    )

    # Champion produced by V3.4/V3.5 research pipeline.
    v36_champion_directory: str = (
        "artifacts/v34"
    )

    # Paper order endpoint already protected by
    # V2.5-V2.9 execution guards.
    v36_paper_order_url: str = (
        "http://127.0.0.1:8000/"
        "api/v1/paper/orders"
    )

    v36_account_id: str = ""

    # Execution sizing.
    v36_order_quantity: float = 1.0

    # Require high-confidence champion predictions.
    v36_minimum_execution_confidence: float = 0.60

    # Avoid rapid repeat orders.
    v36_signal_cooldown_seconds: int = 300

    # Never execute on data older than this.
    v36_maximum_market_data_age_seconds: int = 180

    # Runtime polling.
    v36_cycle_interval_seconds: int = 60

    # Attribution horizon.
    v36_outcome_horizon_bars: int = 5

    # Files intentionally live under ignored artifacts/.
    v36_decision_log_path: str = (
        "artifacts/v36/decisions.jsonl"
    )

    v36_execution_log_path: str = (
        "artifacts/v36/executions.jsonl"
    )

    v36_outcome_log_path: str = (
        "artifacts/v36/outcomes.jsonl"
    )
        # Version 3.7 autonomous paper platform
    v37_autonomous_enabled: bool = True

    # V3.7 is intentionally paper-only.
    v37_live_money_enabled: bool = False

    v37_symbol: str = "AAPL"
    v37_interval: str = "1m"

    v37_artifact_directory: str = (
        "artifacts/v37"
    )

    # Runtime cadence
    v37_ingestion_interval_seconds: int = 30
    v37_execution_interval_seconds: int = 60
    v37_attribution_interval_seconds: int = 60
    v37_health_interval_seconds: int = 30

    # Adaptive learning cadence.
    # 21,600 seconds = 6 hours.
    v37_learning_interval_seconds: int = 21_600

    # Do not retrain unless meaningful new data exists.
    v37_learning_minimum_new_bars: int = 250

    # Historical refresh used by each incremental ingestion.
    v37_ingestion_lookback_days: int = 2

    # Recovery/backoff
    v37_initial_backoff_seconds: int = 15
    v37_maximum_backoff_seconds: int = 300

    # Health
    v37_market_data_warning_age_seconds: int = 180
    v37_market_data_failure_age_seconds: int = 600

    # Persisted runtime state.
    v37_state_path: str = (
        "artifacts/v37/state.json"
    )

    v37_health_path: str = (
        "artifacts/v37/health.json"
    )

    v37_event_log_path: str = (
        "artifacts/v37/events.jsonl"
    )

    # Presence of this file stops autonomous work.
    v37_kill_switch_path: str = (
        "artifacts/v37/STOP"
    )

    # Current research generation that can create
    # the champion V3.6 consumes.
    v37_learning_script: str = (
        "scripts/run_v34_learning_cycle.py"
    )

    v37_ingestion_script: str = (
        "scripts/ingest_alpaca_history_v30.py"
    )

    v37_execution_script: str = (
        "scripts/run_v36_paper_cycle.py"
    )

    v37_attribution_script: str = (
        "scripts/attribute_v36_outcomes.py"
    )

        # Version 3.8 multi-market learning

    v38_learning_enabled: bool = True

    v38_learning_symbol: str = "AAPL"

    v38_context_symbols: str = "SPY,QQQ"

    v38_learning_interval: str = "1m"

    v38_learning_artifact_directory: str = (
        "artifacts/v38"
    )

    v38_minimum_rows: int = 10_000

    v38_forward_horizon_bars: int = 10

    v38_target_minimum_edge_bps: float = 5.0

    v38_holdout_fraction: float = 0.20

    v38_walk_forward_folds: int = 5

    v38_purge_rows: int = 10

    v38_round_trip_cost_bps: float = 4.0

    v38_minimum_balanced_accuracy: float = 0.35

    v38_minimum_macro_f1: float = 0.30

    v38_minimum_net_return: float = 0.0

    v38_minimum_positive_fold_fraction: float = 0.60

    v38_minimum_trades: int = 20

    v38_maximum_holdout_drawdown: float = 0.20

    v38_minimum_promotion_improvement: float = 0.01

    v38_mlflow_tracking_uri: str = (
        "http://127.0.0.1:5000"
    )

    v38_mlflow_experiment_name: str = (
        "finai-v38-multimarket-learning"
    )
    v38_long_probability_thresholds: str = (
        "0.40,0.45,0.50,0.55,0.60,0.65"
    )

    v38_short_probability_thresholds: str = (
        "0.40,0.45,0.50,0.55,0.60,0.65"
    )

    v38_inner_calibration_fraction: float = 0.20

    v38_execution_enabled: bool = True

    v38_live_money_enabled: bool = False

    v38_order_quantity: float = 1.0

    v38_paper_order_url: str = (
        "http://127.0.0.1:8000/"
        "api/v1/paper/orders"
    )

    v38_account_id: str = ""

    v38_maximum_market_data_age_seconds: int = 180

    v38_decision_log_path: str = (
        "artifacts/v38/decisions.jsonl"
    )

    v38_execution_log_path: str = (
        "artifacts/v38/executions.jsonl"
    )
        # Version 3.9 regime-aware ensemble learning

    v39_learning_enabled: bool = True

    v39_learning_symbol: str = "AAPL"

    v39_learning_interval: str = "1m"

    v39_learning_artifact_directory: str = (
        "artifacts/v39"
    )

    v39_minimum_rows: int = 10_000

    v39_forward_horizon_bars: int = 10

    v39_target_minimum_edge_bps: float = 5.0

    v39_holdout_fraction: float = 0.20

    v39_walk_forward_folds: int = 5

    v39_purge_rows: int = 10

    v39_round_trip_cost_bps: float = 4.0

    v39_long_probability_thresholds: str = (
        "0.40,0.45,0.50,0.55,0.60,0.65"
    )

    v39_short_probability_thresholds: str = (
        "0.40,0.45,0.50,0.55,0.60,0.65"
    )

    v39_inner_calibration_fraction: float = 0.20

    # Each market regime needs enough observations
    # before receiving its own fitted estimator.
    v39_minimum_regime_rows: int = 1_000

    # Promotion gates
    v39_minimum_balanced_accuracy: float = 0.35

    v39_minimum_macro_f1: float = 0.30

    v39_minimum_net_return: float = 0.0

    v39_minimum_positive_fold_fraction: float = 0.60

    v39_minimum_trades: int = 20

    v39_maximum_holdout_drawdown: float = 0.20

    v39_minimum_promotion_improvement: float = 0.01

    # Execution remains paper-only.
    v39_execution_enabled: bool = True

    v39_live_money_enabled: bool = False

    v39_order_quantity: float = 1.0

    v39_paper_order_url: str = (
        "http://127.0.0.1:8000/"
        "api/v1/paper/orders"
    )

    v39_account_id: str = ""

    v39_maximum_market_data_age_seconds: int = 180

    v39_decision_log_path: str = (
        "artifacts/v39/decisions.jsonl"
    )

    v39_execution_log_path: str = (
        "artifacts/v39/executions.jsonl"
    )

        # =========================================================
    # V4.0 - prospective shadow validation
    # =========================================================

    v40_learning_enabled: bool = True

    v40_learning_symbol: str = "AAPL"
    v40_learning_interval: str = "1m"

    v40_learning_artifact_directory: str = (
        "artifacts/v40"
    )

    v40_shadow_directory: str = (
        "artifacts/v40/shadow"
    )

    v40_minimum_rows: int = 50_000

    v40_forward_horizon_bars: int = 5

    v40_target_minimum_edge_bps: float = 8.0

    v40_holdout_fraction: float = 0.20

    v40_walk_forward_folds: int = 5

    v40_purge_rows: int = 10

    v40_round_trip_cost_bps: float = 2.0

    v40_long_probability_thresholds: str = (
        "0.34,0.38,0.42,0.46,0.50,"
        "0.54,0.58,0.62"
    )

    v40_short_probability_thresholds: str = (
        "0.34,0.38,0.42,0.46,0.50,"
        "0.54,0.58,0.62"
    )

    v40_inner_calibration_fraction: float = 0.20

    v40_minimum_balanced_accuracy: float = 0.36

    v40_minimum_macro_f1: float = 0.28

    v40_minimum_net_return: float = 0.0

    v40_minimum_positive_fold_fraction: float = 0.60

    v40_minimum_trades: int = 100

    v40_maximum_holdout_drawdown: float = 0.35

    v40_minimum_promotion_improvement: float = 0.01

    v40_minimum_regime_rows: int = 500

    v40_shadow_minimum_observations: int = 1_000

    v40_shadow_minimum_trades: int = 25

    v40_shadow_minimum_net_return: float = 0.0

    v40_shadow_maximum_drawdown: float = 0.15

    v41_learning_symbol: str = "AAPL"

    v41_learning_interval: str = "1m"

    v41_learning_artifact_directory: str = (
        "artifacts/v41"
    )
    v41_shadow_directory: str = (
        "artifacts/v41/shadow"
    )

    v41_minimum_rows: int = 45_000

    v41_forward_horizon_bars: int = 15

    v41_target_minimum_edge_bps: float = 3.0

    v41_round_trip_cost_bps: float = 2.0

    v41_holdout_fraction: float = 0.20

    v41_walk_forward_folds: int = 5

    v41_purge_rows: int = 20

    v41_inner_calibration_fraction: float = 0.20

    v41_long_probability_thresholds: str = (
        "0.36,0.40,0.44,0.48,0.52,0.56"
    )

    v41_short_probability_thresholds: str = (
        "0.36,0.40,0.44,0.48,0.52,0.56"
    )

    v41_minimum_balanced_accuracy: float = 0.36

    v41_minimum_macro_f1: float = 0.28

    v41_minimum_net_return: float = 0.0

    v41_minimum_positive_fold_fraction: float = 0.60

    v41_minimum_trades: int = 100

    v41_maximum_holdout_drawdown: float = 0.35

    v41_minimum_promotion_improvement: float = 0.01

    v41_minimum_regime_rows: int = 1_000

    v41_shadow_minimum_observations: int = 100

    v41_shadow_minimum_net_return: float = 0.0

    v41_shadow_maximum_drawdown: float = 0.20

    v41_shadow_minimum_win_rate: float = 0.50

@lru_cache
def get_settings() -> Settings:
    return Settings()
