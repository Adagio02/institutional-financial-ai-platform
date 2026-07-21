from __future__ import annotations

from pathlib import Path

from finai.data.connectors.french_factors import FrenchFactorConnector


def main() -> int:
    output_dir = Path("data/bronze/factors")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "fama_french_5_daily.parquet"
    temporary_path = output_path.with_suffix(".parquet.tmp")

    connector = FrenchFactorConnector()
    frame = connector.fetch_daily_five_factor()

    if frame.empty:
        raise RuntimeError("The Fama-French connector returned no rows")

    required_columns = {
        "date",
        "Mkt-RF",
        "SMB",
        "HML",
        "RMW",
        "CMA",
        "RF",
    }

    missing = required_columns.difference(frame.columns)

    if missing:
        raise RuntimeError(
            f"Fama-French data is missing columns: {sorted(missing)}"
        )

    frame.to_parquet(temporary_path, index=False)
    temporary_path.replace(output_path)

    print(
        f"[OK] Fama-French daily five-factor data: "
        f"{len(frame):,} rows -> {output_path}"
    )

    print(frame.tail())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())