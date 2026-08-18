from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from finai.core.config import get_settings
from finai.infrastructure.database.engine import Base

from finai.infrastructure.database.models.ingestion_job import (
    IngestionJobModel,  # noqa: F401
)

from finai.infrastructure.database.models.dataset_version import (
    DatasetVersionModel,  # noqa: F401
)
from finai.infrastructure.database.models.feature_set import (
    FeatureSetModel,  # noqa: F401
)
from finai.infrastructure.database.models.feature_value import (
    FeatureValueModel,  # noqa: F401
)
from finai.infrastructure.database.models.evaluation_result import (
    EvaluationResultModel,  # noqa: F401
)
from finai.infrastructure.database.models.model_artifact import (
    ModelArtifactModel,  # noqa: F401
)
from finai.infrastructure.database.models.training_run import (
    TrainingRunModel,  # noqa: F401
)
from finai.infrastructure.database.models.model_card import (
    ModelCardModel,  # noqa: F401
)
from finai.infrastructure.database.models.prediction import (
    PredictionModel,  # noqa: F401
)
from finai.infrastructure.database.models.prediction_explanation import (
    PredictionExplanationModel,  # noqa: F401
)
from finai.infrastructure.database.models.backtest_run import (
    BacktestRunModel,  # noqa: F401
)
from finai.infrastructure.database.models.portfolio_snapshot import (
    PortfolioSnapshotModel,  # noqa: F401
)
from finai.infrastructure.database.models.simulated_trade import (
    SimulatedTradeModel,  # noqa: F401
)
from finai.infrastructure.database.models.execution_fill import (
    ExecutionFillModel,  # noqa: F401
)
from finai.infrastructure.database.models.order import (
    OrderModel,  # noqa: F401
)
from finai.infrastructure.database.models.paper_account import (
    PaperAccountModel,  # noqa: F401
)
from finai.infrastructure.database.models.paper_portfolio_snapshot import (
    PaperPortfolioSnapshotModel,  # noqa: F401
)
from finai.infrastructure.database.models.paper_position import (
    PaperPositionModel,  # noqa: F401
)
from finai.infrastructure.database.models.execution_audit import (
    ExecutionAuditModel,  # noqa: F401
)
from finai.infrastructure.database.models.trading_control import (
    TradingControlModel,  # noqa: F401
)
from finai.infrastructure.database.models.trade_proposal import (
    TradeProposalModel,  # noqa: F401
)
from finai.infrastructure.database.models.strategy_attribution import (
    StrategyAttributionModel,  # noqa: F401
)
from finai.infrastructure.database.models.strategy_policy import (
    StrategyPolicyModel,  # noqa: F401
)
from finai.infrastructure.database.models.strategy_position import (
    StrategyPositionModel,  # noqa: F401
)
from finai.infrastructure.database.models.strategy_run import (
    StrategyRunModel,  # noqa: F401
)
from finai.infrastructure.database.models.strategy_run_item import (
    StrategyRunItemModel,  # noqa: F401
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()

config.set_main_option(
    "sqlalchemy.url",
    str(settings.database_url).replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
