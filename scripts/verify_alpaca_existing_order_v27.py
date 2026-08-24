from __future__ import annotations

import sys

from finai.core.config import (
    get_settings,
)
from finai.infrastructure.execution.alpaca_broker_factory import (
    create_alpaca_paper_broker,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python "
            "verify_alpaca_existing_order_v27.py "
            "<client_order_id>"
        )

    client_order_id = (
        sys.argv[1]
        .strip()
    )

    settings = get_settings()

    broker = (
        create_alpaca_paper_broker(
            settings=settings
        )
    )

    snapshot = (
        broker
        .get_snapshot_by_client_order_id(
            client_order_id=(
                client_order_id
            )
        )
    )

    print(
        "Existing broker order:"
    )

    print(
        "Broker ID:",
        snapshot.broker_order_id,
    )

    print(
        "Client ID:",
        snapshot.client_order_id,
    )

    print(
        "Symbol:",
        snapshot.symbol,
    )

    print(
        "Status:",
        snapshot.raw_status,
    )

    if (
        snapshot.symbol
        != "AAPL"
    ):
        raise RuntimeError(
            "Expected AAPL."
        )

    print(
        "V2.7 existing-order "
        "lookup passed."
    )


if __name__ == "__main__":
    main()