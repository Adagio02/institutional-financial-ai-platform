from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.market_quote_service import (
    MarketQuoteService,
)
from finai.application.services.paper_execution_service import (
    PaperExecutionService,
)
from finai.application.services.portfolio_service import (
    PortfolioService,
)
from finai.application.services.pre_trade_risk_service import (
    PreTradeRiskService,
)
from finai.application.services.trading_control_service import (
    TradingControlService,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
    TimeInForce,
)
from finai.domain.execution.validation import (
    validate_order_request,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.market_data.execution_quote import (
    get_executable_reference_price,
)
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)


class OrderService:
    def __init__(
        self,
        *,
        session: Session,
        commission_bps: float,
        slippage_bps: float,
        risk_limits: PortfolioRiskLimits,
        maximum_quote_age_seconds: int,
        quote_interval: BarInterval,
        synthetic_spread_bps: float,
        trading_control_maximum_daily_loss_fraction: float,
        trading_control_maximum_gross_exposure_fraction: float,
        trading_control_maximum_symbol_fraction: float,
        trading_control_maximum_order_fraction: float,
        partial_fill_enabled: bool = False,
        initial_fill_fraction: float = 1.0,
        execution_mode: str = "paper",
        pre_trade_risk_enabled: bool = True,
        pre_trade_maximum_order_quantity: float = 100.0,
        pre_trade_maximum_order_notional: float = 25_000.0,
        pre_trade_maximum_position_notional: float = 50_000.0,
        pre_trade_maximum_buying_power_fraction: float = 0.10,
    ) -> None:
        self._instrument_repository = (
            InstrumentRepository(
                session
            )
        )

        self._account_repository = (
            PaperAccountRepository(
                session
            )
        )

        self._order_repository = (
            OrderRepository(
                session
            )
        )

        self._position_repository = (
            PaperPositionRepository(
                session
            )
        )

        self._portfolio_service = (
            PortfolioService(
                session=session
            )
        )

        # V2.9 deterministic pre-trade risk service.
        self._pre_trade_risk_service = (
            PreTradeRiskService(
                enabled=(
                    pre_trade_risk_enabled
                ),
                maximum_order_quantity=(
                    pre_trade_maximum_order_quantity
                ),
                maximum_order_notional=(
                    pre_trade_maximum_order_notional
                ),
                maximum_position_notional=(
                    pre_trade_maximum_position_notional
                ),
                maximum_buying_power_fraction=(
                    pre_trade_maximum_buying_power_fraction
                ),
            )
        )

        self._market_quote_service = (
            MarketQuoteService(
                session=session,
                maximum_quote_age_seconds=(
                    maximum_quote_age_seconds
                ),
                quote_interval=(
                    quote_interval
                ),
                synthetic_spread_bps=(
                    synthetic_spread_bps
                ),
                execution_mode=(
                    execution_mode
                ),
            )
        )

        self._execution_service = (
            PaperExecutionService(
                session=session,
                commission_bps=(
                    commission_bps
                ),
                slippage_bps=(
                    slippage_bps
                ),
                partial_fill_enabled=(
                    partial_fill_enabled
                ),
                initial_fill_fraction=(
                    initial_fill_fraction
                ),
                execution_mode=(
                    execution_mode
                ),
            )
        )

        self._trading_control_service = (
            TradingControlService(
                session=session,
                default_maximum_daily_loss_fraction=(
                    trading_control_maximum_daily_loss_fraction
                ),
                default_maximum_gross_exposure_fraction=(
                    trading_control_maximum_gross_exposure_fraction
                ),
                default_maximum_symbol_fraction=(
                    trading_control_maximum_symbol_fraction
                ),
                default_maximum_order_fraction=(
                    trading_control_maximum_order_fraction
                ),
            )
        )

        # Keep this because other callers may still pass the
        # existing portfolio-risk configuration to OrderService.
        self._risk_limits = risk_limits

    def submit(
        self,
        *,
        account_id: UUID,
        client_order_id: str | None,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        limit_price: float | None,
        time_in_force: TimeInForce,
        strategy_key: str | None = None,
    ):
        validate_order_request(
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
        )

        # --------------------------------------------------
        # Account
        # --------------------------------------------------

        account = (
            self._account_repository
            .get_by_id(
                account_id
            )
        )

        if account is None:
            raise LookupError(
                "Paper account not found: "
                f"{account_id}"
            )

        # --------------------------------------------------
        # Idempotency
        # --------------------------------------------------

        normalized_client_order_id = None

        if client_order_id is not None:
            normalized_client_order_id = (
                client_order_id
                .strip()
            )

            if not normalized_client_order_id:
                normalized_client_order_id = None

        if normalized_client_order_id is not None:
            existing_order = (
                self._order_repository
                .get_by_client_order_id(
                    account_id=(
                        account.id
                    ),
                    client_order_id=(
                        normalized_client_order_id
                    ),
                )
            )

            if existing_order is not None:
                return existing_order

        # --------------------------------------------------
        # Instrument
        # --------------------------------------------------

        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        if not normalized_symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        instrument = (
            self._instrument_repository
            .get_model_by_symbol(
                normalized_symbol
            )
        )

        if instrument is None:
            raise LookupError(
                "Instrument not found: "
                f"{normalized_symbol}"
            )

        # --------------------------------------------------
        # Quote
        # --------------------------------------------------

        quote = (
            self._market_quote_service
            .get_quote(
                symbol=(
                    instrument.symbol
                )
            )
        )

        reference_price = (
            get_executable_reference_price(
                quote=quote,
                side=side,
            )
        )

        # --------------------------------------------------
        # Existing position
        # --------------------------------------------------

        position = (
            self._position_repository
            .get(
                account_id=(
                    account.id
                ),
                instrument_id=(
                    instrument.id
                ),
            )
        )

        current_position_quantity = 0.0

        if position is not None:
            current_position_quantity = float(
                position.quantity
            )

        # --------------------------------------------------
        # V2.9 PRE-TRADE RISK GATE
        #
        # This must happen before order persistence and
        # before broker execution.
        # --------------------------------------------------

        self._pre_trade_risk_service.require_approval(
            symbol=(
                normalized_symbol
            ),
            side=(
                side.value
            ),
            quantity=(
                quantity
            ),
            reference_price=(
                reference_price
            ),
            current_position_quantity=(
                current_position_quantity
            ),
        )

        # --------------------------------------------------
        # Persist accepted pre-trade order
        # --------------------------------------------------

        order = (
            self._order_repository
            .create(
                account_id=(
                    account.id
                ),
                instrument_id=(
                    instrument.id
                ),
                client_order_id=(
                    normalized_client_order_id
                ),
                symbol=(
                    instrument.symbol
                ),
                side=(
                    side.value
                ),
                order_type=(
                    order_type.value
                ),
                quantity=(
                    quantity
                ),
                limit_price=(
                    limit_price
                ),
                time_in_force=(
                    time_in_force.value
                ),
                reference_price=(
                    reference_price
                ),
                reference_price_timestamp=(
                    quote.timestamp
                ),
                reference_price_provider=(
                    quote.provider
                ),
                strategy_key=(
                    strategy_key
                ),
            )
        )

        # --------------------------------------------------
        # Portfolio state
        # --------------------------------------------------

        portfolio = (
            self._portfolio_service
            .summarize(
                account_id=(
                    account.id
                ),
                prices={
                    instrument.symbol: (
                        quote.midpoint
                    ),
                },
            )
        )

        current_position_notional = (
            current_position_quantity
            * reference_price
        )

        current_symbol_exposure = abs(
            current_position_notional
        )

        proposed_order_notional = abs(
            quantity
            * reference_price
        )

        # --------------------------------------------------
        # Existing centralized trading controls
        # --------------------------------------------------

        control_decision = (
            self._trading_control_service
            .evaluate(
                account_id=(
                    account.id
                ),
                current_equity=(
                    portfolio[
                        "equity"
                    ]
                ),
                current_gross_exposure=(
                    portfolio[
                        "gross_exposure"
                    ]
                ),
                current_symbol_exposure=(
                    current_symbol_exposure
                ),
                proposed_order_notional=(
                    proposed_order_notional
                ),
            )
        )

        if not control_decision.approved:
            return (
                self._order_repository
                .mark_rejected(
                    order,
                    reason=(
                        control_decision.message
                        or (
                            "Trading control "
                            "rejected order."
                        )
                    ),
                )
            )

        # --------------------------------------------------
        # Broker execution
        # --------------------------------------------------

        self._execution_service.execute(
            order=order,
            reference_price=(
                reference_price
            ),
        )

        refreshed_order = (
            self._order_repository
            .get_by_id(
                order.id
            )
        )

        if refreshed_order is None:
            raise LookupError(
                "Order not found after "
                "execution: "
                f"{order.id}"
            )

        return refreshed_order