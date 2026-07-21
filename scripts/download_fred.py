from __future__ import annotations

import sys
from pathlib import Path

from finai.data.connectors.fred import FredConnector


SERIES = [
    "DFF",
    "CPIAUCSL",
    "UNRATE",
    "GDPC1",
    "DGS10",
    "DGS2",
    "BAA10Y",
    "VIXCLS",
]


def main() -> int:
    output_dir = Path("data/bronze/fred")
    output_dir.mkdir(parents=True, exist_ok=True)

    connector = FredConnector()
    failures: list[str] = []

    for series_id in SERIES:
        try:
            frame = connector.fetch(series_id)

            if frame.is_empty():
                raise RuntimeError("FRED returned an empty dataset")

            output_path = output_dir / f"{series_id}.parquet"
            temporary_path = output_path.with_suffix(".parquet.tmp")

            frame.write_parquet(temporary_path)
            temporary_path.replace(output_path)

            print(
                f"[OK] {series_id}: "
                f"{frame.height:,} rows -> {output_path}"
            )

        except Exception as exc:
            failures.append(series_id)
            print(f"[FAILED] {series_id}: {exc}", file=sys.stderr)

    if failures:
        print(
            f"Failed series: {', '.join(failures)}",
            file=sys.stderr,
        )
        return 1

    print("All FRED series downloaded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())