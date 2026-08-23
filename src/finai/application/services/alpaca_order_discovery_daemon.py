from __future__ import annotations

import logging
from threading import Event

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


logger = logging.getLogger(
    __name__
)


class AlpacaOrderDiscoveryDaemon:
    def __init__(
        self,
        *,
        shutdown_event: (
            Event | None
        ) = None,
    ) -> None:
        self._settings = (
            get_settings()
        )

        if not (
            self._settings
            .alpaca_order_discovery_enabled
        ):
            raise ValueError(
                "Alpaca order discovery "
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

        if (
            self._settings
            .alpaca_order_discovery_interval_seconds
            <= 0
        ):
            raise ValueError(
                "Discovery interval "
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
            .alpaca_order_discovery_interval_seconds
        )

        logger.info(
            "Alpaca order discovery "
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
                    "Alpaca discovery "
                    "completed. "
                    "remote=%s "
                    "local=%s "
                    "matched=%s "
                    "synchronized=%s "
                    "refreshed=%s "
                    "broker_only=%s "
                    "local_open_missing=%s",
                    result.remote_orders,
                    result.local_orders,
                    result.matched,
                    result.synchronized,
                    result.refreshed,
                    len(
                        result.broker_only
                    ),
                    len(
                        result
                        .local_open_missing_remote
                    ),
                )

                for orphan in (
                    result.broker_only
                ):
                    logger.warning(
                        "Broker-only Alpaca "
                        "order detected. "
                        "broker_order_id=%s "
                        "client_order_id=%s "
                        "symbol=%s "
                        "status=%s",
                        orphan
                        .broker_order_id,
                        orphan
                        .client_order_id,
                        orphan.symbol,
                        orphan.status,
                    )

                for order_id in (
                    result
                    .local_open_missing_remote
                ):
                    logger.warning(
                        "Local open Alpaca "
                        "order is absent from "
                        "broker open-order list. "
                        "order_id=%s",
                        order_id,
                    )

            except Exception:  # noqa: BLE001
                logger.exception(
                    "Alpaca order discovery "
                    "cycle failed."
                )

            self._shutdown_event.wait(
                interval
            )

        logger.info(
            "Alpaca order discovery "
            "daemon stopped."
        )

    def _run_once(
        self,
    ):
        session = SessionLocal()

        try:
            client = AlpacaPaperClient(
                api_key=(
                    self._settings
                    .alpaca_api_key
                ),
                secret_key=(
                    self._settings
                    .alpaca_secret_key
                ),
                base_url=(
                    self._settings
                    .alpaca_base_url
                ),
                timeout_seconds=(
                    self._settings
                    .alpaca_request_timeout_seconds
                ),
            )

            broker = AlpacaPaperBroker(
                client=client
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

            discovery_service = (
                AlpacaOrderDiscoveryService(
                    session=session,
                    broker=broker,
                    execution_service=(
                        execution_service
                    ),
                    limit=(
                        self._settings
                        .alpaca_order_discovery_limit
                    ),
                    direction=(
                        self._settings
                        .alpaca_order_discovery_direction
                    ),
                )
            )

            return (
                discovery_service
                .discover()
            )

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
        AlpacaOrderDiscoveryDaemon()
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