from finai.application.services.alpaca_order_discovery_service import (
    AlpacaOrderDiscoveryService,
)
from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
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

        status = str(
            account.get(
                "status",
                "",
            )
        ).upper()

        if status != "ACTIVE":
            raise RuntimeError(
                "Alpaca paper account "
                "is not ACTIVE."
            )

        broker = (
            AlpacaPaperBroker(
                client=client
            )
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
            )
        )

        result = (
            discovery_service
            .discover()
        )

        print(
            "Version 2.3 Alpaca "
            "order discovery passed."
        )

        print(
            "Remote orders:",
            result.remote_orders,
        )

        print(
            "Remote open orders:",
            result.remote_open_orders,
        )

        print(
            "Local Alpaca orders:",
            result.local_orders,
        )

        print(
            "Matched:",
            result.matched,
        )

        print(
            "Synchronized:",
            result.synchronized,
        )

        print(
            "Refreshed:",
            result.refreshed,
        )

        print(
            "Broker-only:",
            len(
                result.broker_only
            ),
        )

        print(
            "Local open missing remote:",
            len(
                result
                .local_open_missing_remote
            ),
        )

        if result.broker_only:
            print(
                ""
            )

            print(
                "Broker-only orders "
                "were detected."
            )

            print(
                "They were NOT "
                "automatically imported."
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
                    orphan.status,
                )

    finally:
        session.close()


if __name__ == "__main__":
    main()