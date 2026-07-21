from __future__ import annotations

import argparse
import json
from pathlib import Path

from finai.data.connectors.sec import SecConnector


DEFAULT_COMPANIES = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "JPM": "0000019617",
    "XOM": "0000034088",
    "UNH": "0000731766",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download SEC submissions and Company Facts."
    )

    parser.add_argument(
        "--ticker",
        choices=sorted(DEFAULT_COMPANIES),
        default="AAPL",
    )

    return parser.parse_args()


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    temporary_path.replace(path)


def main() -> int:
    args = parse_arguments()

    ticker = args.ticker
    cik = DEFAULT_COMPANIES[ticker]

    connector = SecConnector()

    submissions = connector.submissions(cik)
    company_facts = connector.company_facts(cik)

    output_dir = Path("data/bronze/sec") / ticker
    output_dir.mkdir(parents=True, exist_ok=True)

    write_json_atomic(
        output_dir / "submissions.json",
        submissions,
    )

    write_json_atomic(
        output_dir / "company_facts.json",
        company_facts,
    )

    print(
        f"[OK] SEC data downloaded for {ticker} "
        f"(CIK {cik}) -> {output_dir}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())