from finai.core.config import (
    get_settings,
)
from finai.domain.execution.alpaca_account_guard import (
    AlpacaAccountGuard,
)
from finai.domain.execution.enums import (
    OrderSide,
)
from finai.infrastructure.execution.alpaca_client import (
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

    account = client.get_account()

    guard = AlpacaAccountGuard(
        require_active=(
            settings
            .alpaca_account_guard_require_active
        ),
        maximum_buying_power_fraction=(
            settings
            .alpaca_account_guard_maximum_buying_power_fraction
        ),
        require_positive_buying_power=(
            settings
            .alpaca_account_guard_require_positive_buying_power
        ),
    )

    buying_power = float(
        account.get(
            "buying_power",
            0.0,
        )
    )

    if buying_power <= 0:
        raise RuntimeError(
            "Alpaca account has no "
            "positive buying power."
        )

    fraction = (
        settings
        .alpaca_account_guard_maximum_buying_power_fraction
    )

    test_notional = min(
        buying_power
        * fraction
        * 0.50,
        100.0,
    )

    if test_notional <= 0:
        raise RuntimeError(
            "Could not calculate "
            "a positive test notional."
        )

    result = (
        guard.validate_order(
            account=account,
            side=(
                OrderSide.BUY
            ),
            quantity=1.0,
            reference_price=(
                test_notional
            ),
        )
    )

    print(
        "Version 2.5 Alpaca "
        "account guard passed."
    )

    print(
        "Status:",
        result.status,
    )

    print(
        "Trading blocked:",
        result.trading_blocked,
    )

    print(
        "Account blocked:",
        result.account_blocked,
    )

    print(
        "Buying power:",
        result.buying_power,
    )

    print(
        "Cash:",
        result.cash,
    )

    print(
        "Equity:",
        result.equity,
    )

    print(
        "Maximum guarded order:",
        result
        .maximum_allowed_order_notional,
    )

    print(
        "Verifier order notional:",
        result
        .estimated_order_notional,
    )


if __name__ == "__main__":
    main()