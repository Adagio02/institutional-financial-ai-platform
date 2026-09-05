from finai.application.services.alpaca_order_discovery_service import (
    AlpacaOrderDiscoveryService,
)
from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.application.services.alpaca_orphan_recovery_service import (
    AlpacaOrphanRecoveryService,
)
from finai.core.config import (
    get_settings,
)
from finai.infrastructure.database.engine import (
    SessionLocal,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaPaperClient,
)


def main() -> None:
    settings = get_settings()

    session = SessionLocal()

    try:
        client = AlpacaPaperClient(
            api_key=(
                settings
                .alpaca_api_key
            ),
            secret_key=(
                settings
                .alpaca_secret_key
            ),
            base_url=(
                settings
                .alpaca_base_url
            ),
            timeout_seconds=(
                settings
                .alpaca_request_timeout_seconds
            ),
        )

        account = (
            client.get_account()
        )

        account_status = str(
            account.get(
                "status",
                "",
            )
        ).upper()

        if account_status != "ACTIVE":
            raise RuntimeError(
                "Alpaca paper account "
                "is not ACTIVE."
            )

        broker = AlpacaPaperBroker(
            client=client
        )

        execution_service = (
            AlpacaOrderExecutionService(
                session=session,
                broker=broker,
                commission_bps=(
                    settings
                    .alpaca_execution_commission_bps
                ),
                sync_on_submit=False,
            )
        )

        recovery_service = (
            AlpacaOrphanRecoveryService(
                session=session,
                broker=broker,
                execution_service=(
                    execution_service
                ),
                require_symbol_match=(
                    settings
                    .alpaca_orphan_recovery_require_symbol_match
                ),
                require_quantity_match=(
                    settings
                    .alpaca_orphan_recovery_require_quantity_match
                ),
            )
        )

        discovery_service = (
            AlpacaOrderDiscoveryService(
                session=session,
                broker=broker,
                execution_service=(
                    execution_service
                ),
                limit=(
                    settings
                    .alpaca_order_discovery_limit
                ),
                direction=(
                    settings
                    .alpaca_order_discovery_direction
                ),
                orphan_recovery_service=(
                    recovery_service
                ),
            )
        )

        result = (
            discovery_service
            .discover()
        )

        print(
            "Version 2.4 Alpaca "
            "orphan recovery passed."
        )

        print(
            "Remote orders:",
            result.remote_orders,
        )

        print(
            "Matched:",
            result.matched,
        )

        print(
            "Recovered:",
            result.recovered,
        )

        print(
            "Still broker-only:",
            len(
                result.broker_only
            ),
        )

        if result.broker_only:
            print(
                ""
            )

            print(
                "Unresolved broker-only "
                "orders:"
            )

            for orphan in (
                result.broker_only
            ):
                print(
                    "-",
                    orphan
                    .broker_order_id,
                    orphan
                    .client_order_id,
                    orphan.symbol,
                    orphan.reason,
                )

    finally:
        session.close()


if __name__ == "__main__":
    main()