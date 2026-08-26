from pathlib import Path

from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    champion_directory = Path(
        settings.v35_champion_directory
    )

    champion_metadata = (
        champion_directory
        / "champion.json"
    )

    print(
        "=== FINAI V3.5 READINESS ==="
    )

    print(
        "Inference enabled:",
        settings.v35_inference_enabled,
    )

    print(
        "Shadow trading:",
        settings.v35_shadow_trading_enabled,
    )

    print(
        "Broker submission:",
        settings.v35_broker_submission_enabled,
    )

    print(
        "Champion directory:",
        champion_directory,
    )

    print(
        "Champion metadata exists:",
        champion_metadata.exists(),
    )

    if (
        settings
        .v35_broker_submission_enabled
    ):
        print()
        print(
            "WARNING: broker submission "
            "is enabled."
        )

    else:
        print()
        print(
            "SAFE MODE: V3.5 cannot "
            "submit broker orders."
        )

    if not champion_metadata.exists():
        print()
        print(
            "NO CHAMPION:"
        )

        print(
            "Continue collecting real data "
            "and running research cycles."
        )

        print(
            "Do not weaken promotion gates "
            "simply to create a champion."
        )

        return

    print()
    print(
        "Champion metadata found."
    )

    print(
        "V3.5 can proceed to "
        "shadow inference."
    )


if __name__ == "__main__":
    main()