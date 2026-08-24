from __future__ import annotations

import sys

from finai.core.config import (
    get_settings,
)
from finai.domain.execution.alpaca_idempotency_guard import (
    AlpacaIdempotencyGuard,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaOrderNotFoundError,
    AlpacaPaperClient,
)


def main() -> None:
    settings = get_settings()

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

    guard = AlpacaIdempotencyGuard(
        require_order_match=(
            settings
            .alpaca_idempotency_require_order_match
        )
    )

    test_client_order_id = (
        "v27-verifier-does-not-exist-"
        "0000000000000000"
    )

    normalized = (
        guard.validate_client_order_id(
            test_client_order_id
        )
    )

    print(
        "Version 2.7 Alpaca "
        "idempotency verifier."
    )

    print(
        "Guard enabled:",
        settings
        .alpaca_idempotency_guard_enabled,
    )

    print(
        "Lookup before submit:",
        settings
        .alpaca_idempotency_lookup_before_submit,
    )

    print(
        "Recover after transport error:",
        settings
        .alpaca_idempotency_recover_after_transport_error,
    )

    print(
        "Client order ID:",
        normalized,
    )

    try:
        client.get_order_by_client_order_id(
            client_order_id=(
                normalized
            )
        )

    except AlpacaOrderNotFoundError:
        print(
            "Alpaca client-order lookup "
            "endpoint is reachable."
        )

        print(
            "Synthetic verifier order "
            "was correctly not found."
        )

    except Exception as error:
        print(
            "Unexpected Alpaca "
            "lookup failure:",
            error,
        )

        sys.exit(1)

    else:
        print(
            "Warning: synthetic verifier "
            "client_order_id unexpectedly "
            "exists at Alpaca."
        )

    print(
        "Version 2.7 Alpaca "
        "idempotency verification passed."
    )


if __name__ == "__main__":
    main()