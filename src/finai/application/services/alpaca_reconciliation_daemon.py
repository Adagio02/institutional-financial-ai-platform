from __future__ import annotations

import logging
from threading import Event

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
from finai.infrastructure.execution.alpaca_broker_factory import (
    create_alpaca_paper_broker,
)


logger = logging.getLogger(
    __name__
)


class AlpacaReconciliationDaemon:
    def __init__(
        self,
        *,
        shutdown_event: Event | None = None,
    ) -> None:
        self._settings = (
            get_settings()
        )

        if not (
            self._settings
            .alpaca_reconciliation_enabled
        ):
            raise ValueError(
                "Alpaca reconciliation "
                "is disabled."
            )

        if not (
            self._settings
            .alpaca_paper_trading_enabled
        ):
            raise ValueError(
                "Alpaca paper trading "
                "is disabled."
            )

        interval = (
            self._settings
            .alpaca_reconciliation_interval_seconds
        )

        if interval <= 0:
            raise ValueError(
                "Reconciliation interval "
                "must be positive."
            )

        self._shutdown_event = (
            shutdown_event
            or Event()
        )

    def request_shutdown(
        self,
    ) -> None:
        self._shutdown_event.set()

    def run(
        self,
    ) -> None:
        interval = (
            self._settings
            .alpaca_reconciliation_interval_seconds
        )

        logger.info(
            "Alpaca reconciliation "
            "daemon started."
        )

        while not (
            self._shutdown_event
            .is_set()
        ):
            try:
                result = (
                    self._run_once()
                )

                logger.info(
                    "Alpaca reconciliation "
                    "completed. "
                    "scanned=%s "
                    "synchronized=%s "
                    "failed=%s",
                    result.scanned,
                    result.synchronized,
                    result.failed,
                )

                for failure in (
                    result.failures
                ):
                    logger.warning(
                        "Alpaca reconciliation "
                        "failure. "
                        "order_id=%s "
                        "broker_order_id=%s "
                        "error=%s",
                        failure.order_id,
                        failure.broker_order_id,
                        failure.error_message,
                    )

            except Exception:  # noqa: BLE001
                logger.exception(
                    "Alpaca reconciliation "
                    "cycle failed."
                )

            self._shutdown_event.wait(
                interval
            )

        logger.info(
            "Alpaca reconciliation "
            "daemon stopped."
        )

    def _run_once(
        self,
    ):
        session = SessionLocal()

        try:
            broker = (
                create_alpaca_paper_broker(
                    settings=(
                        self._settings
                    )
                )
            )

            execution_service = (
                AlpacaOrderExecutionService(
                    session=session,
                    broker=broker,
                    commission_bps=(
                        self._settings
                        .alpaca_execution_commission_bps
                    ),
                    sync_on_submit=False,
                )
            )

            service = (
                AlpacaReconciliationService(
                    session=session,
                    execution_service=(
                        execution_service
                    ),
                    batch_size=(
                        self._settings
                        .alpaca_reconciliation_batch_size
                    ),
                )
            )

            return (
                service
                .reconcile_open_orders()
            )

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s - "
            "%(message)s"
        ),
    )

    daemon = (
        AlpacaReconciliationDaemon()
    )

    try:
        daemon.run()

    except KeyboardInterrupt:
        daemon.request_shutdown()

        logger.info(
            "Keyboard interrupt "
            "received."
        )


if __name__ == "__main__":
    main()