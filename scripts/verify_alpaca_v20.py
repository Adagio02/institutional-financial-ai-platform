from finai.core.config import (
    get_settings,
)
from finai.infrastructure.execution.alpaca_client import (
    ALPACA_PAPER_BASE_URL,
    AlpacaPaperClient,
)


def main() -> None:
    settings = get_settings()

    if (
        settings.alpaca_base_url
        != ALPACA_PAPER_BASE_URL
    ):
        raise RuntimeError(
            "V2.0 requires the Alpaca "
            "paper endpoint."
        )

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
            "Alpaca paper account is "
            "not ACTIVE."
        )

    print(
        "Version 2.0 Alpaca paper "
        "connectivity passed."
    )

    print(
        "Account status:",
        status,
    )

    print(
        "Execution enabled:",
        settings
        .alpaca_execution_enabled,
    )


if __name__ == "__main__":
    main()