from __future__ import annotations

import asyncio
import logging

from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.application.services.alpaca_trade_update_service import (
    AlpacaTradeUpdateService,
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
from finai.infrastructure.execution.alpaca_trade_update_stream import (
    AlpacaTradeUpdateStream,
)


logger = logging.getLogger(
    __name__
)


class AlpacaTradeUpdateDaemon:
    def __init__(
        self,
    ) -> None:
        self._settings = (
            get_settings()
        )

        if not (
            self._settings
            .alpaca_trade_stream_enabled
        ):
            raise ValueError(
                "Alpaca trade stream "
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

        self._stream = (
            AlpacaTradeUpdateStream(
                api_key=(
                    self._settings
                    .alpaca_api_key
                ),
                secret_key=(
                    self._settings
                    .alpaca_secret_key
                ),
                stream_url=(
                    self._settings
                    .alpaca_trade_stream_url
                ),
                open_timeout_seconds=(
                    self._settings
                    .alpaca_trade_stream_open_timeout_seconds
                ),
            )
        )

    async def run(
        self,
    ) -> None:
        reconnect_delay = (
            self._settings
            .alpaca_trade_stream_reconnect_initial_seconds
        )

        maximum_delay = (
            self._settings
            .alpaca_trade_stream_reconnect_maximum_seconds
        )

        while True:
            try:
                logger.info(
                    "Connecting to Alpaca "
                    "paper trade_updates."
                )

                async for message in (
                    self._stream.messages()
                ):
                    reconnect_delay = (
                        self._settings
                        .alpaca_trade_stream_reconnect_initial_seconds
                    )

                    self._process_message(
                        message
                    )

            except asyncio.CancelledError:
                raise

            except Exception:  # noqa: BLE001
                logger.exception(
                    "Alpaca trade-update "
                    "stream disconnected."
                )

                await asyncio.sleep(
                    reconnect_delay
                )

                reconnect_delay = min(
                    reconnect_delay * 2.0,
                    maximum_delay,
                )

    def _process_message(
        self,
        message: dict,
    ) -> None:
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

            service = (
                AlpacaTradeUpdateService(
                    session=session,
                    broker=broker,
                    execution_service=(
                        execution_service
                    ),
                )
            )

            processed = service.process(
                message=message
            )

            if processed:
                logger.info(
                    "Processed Alpaca "
                    "trade update."
                )

        except Exception:  # noqa: BLE001
            session.rollback()

            logger.exception(
                "Failed to process "
                "Alpaca trade update."
            )

        finally:
            session.close()


async def async_main() -> None:
    daemon = (
        AlpacaTradeUpdateDaemon()
    )

    await daemon.run()


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

    try:
        asyncio.run(
            async_main()
        )

    except KeyboardInterrupt:
        logger.info(
            "Alpaca trade-update "
            "daemon stopped."
        )


if __name__ == "__main__":
    main()