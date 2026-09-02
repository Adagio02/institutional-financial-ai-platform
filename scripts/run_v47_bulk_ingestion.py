from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import json

from finai.application.services.v47_bulk_ingestion_factory import (
    build_v47_bulk_ingestion_service,
)
from finai.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill the V4.7 multi-asset universe "
            "from Alpaca into FinAI PostgreSQL."
        )
    )
    parser.add_argument(
        "--interval",
        default="1m",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=390,
        help=(
            "Calendar days to backfill ending now."
        ),
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=14,
        help=(
            "Calendar days per ingestion request window."
        ),
    )
    parser.add_argument(
        "--symbols",
        default="",
        help=(
            "Optional comma-separated symbol subset."
        ),
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=None,
        help=(
            "Optional first-N symbol limit for smoke tests."
        ),
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help=(
            "Ignore saved completed-window checkpoints."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.days < 1:
        raise ValueError(
            "--days must be positive."
        )

    end_time = datetime.now(
        UTC
    )
    start_time = (
        end_time
        - timedelta(
            days=args.days
        )
    )

    symbols = [
        value.strip().upper()
        for value in args.symbols.split(",")
        if value.strip()
    ]

    service = (
        build_v47_bulk_ingestion_service(
            settings=get_settings(),
        )
    )

    result = service.run(
        interval=args.interval,
        start_time=start_time,
        end_time=end_time,
        chunk_days=args.chunk_days,
        symbols=(
            symbols
            if symbols
            else None
        ),
        maximum_symbols=(
            args.max_symbols
        ),
        resume=(
            not args.no_resume
        ),
    )

    print(
        json.dumps(
            asdict(result),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
