from finai.core.config import (
    get_settings,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaPaperClient,
)


def main() -> None:
    settings = get_settings()

    client = AlpacaPaperClient(
        api_key=settings.alpaca_api_key,
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
            "not active."
        )

    print(
        "Alpaca paper connection passed."
    )

    print(
        "Account ID:",
        account.get("id"),
    )

    print(
        "Account status:",
        status,
    )


if __name__ == "__main__":
    main()