from __future__ import annotations

from pathlib import Path

from finai.data.connectors.treasury import TreasuryFiscalConnector


def main() -> int:
    output_dir = Path("data/bronze/treasury")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "average_interest_rates.parquet"
    temporary_path = output_path.with_suffix(".parquet.tmp")

    connector = TreasuryFiscalConnector()
    frame = connector.fetch(page_size=1000)

    if frame.is_empty():
        raise RuntimeError("Treasury Fiscal Data returned no records")

    frame.write_parquet(temporary_path)
    temporary_path.replace(output_path)

    print(
        f"[OK] Treasury data: "
        f"{frame.height:,} rows -> {output_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())