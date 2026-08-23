from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.application.services.alpaca_reconciliation_service import (
    AlpacaReconciliationService,
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

    if not (
        settings
        .alpaca_paper_trading_enabled
    ):
        raise RuntimeError(
            "Alpaca paper integration "
            "must be enabled."
        )

    session = SessionLocal()

    try:
        client = AlpacaPaperClient(
            api_key=(
                settings.alpaca_api_key
            ),
            secret_key=(
                settings.alpaca_secret_key
            ),
            base_url=(
                settings.alpaca_base_url
            ),
            timeout_seconds=(
                settings
                .alpaca_request_timeout_seconds
            ),
        )

        account = client.get_account()

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

        reconciliation_service = (
            AlpacaReconciliationService(
                session=session,
                execution_service=(
                    execution_service
                ),
                batch_size=(
                    settings
                    .alpaca_reconciliation_batch_size
                ),
            )
        )

        result = (
            reconciliation_service
            .reconcile_open_orders()
        )

        print(
            "Version 2.2 Alpaca "
            "reconciliation passed."
        )

        print(
            "Scanned:",
            result.scanned,
        )

        print(
            "Synchronized:",
            result.synchronized,
        )

        print(
            "Failed:",
            result.failed,
        )

        if result.failed:
            for failure in (
                result.failures
            ):
                print(
                    "Failure:",
                    failure.order_id,
                    failure.error_message,
                )

            raise RuntimeError(
                "One or more Alpaca "
                "orders failed reconciliation."
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()