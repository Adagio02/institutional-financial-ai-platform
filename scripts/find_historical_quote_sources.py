from pathlib import Path
import csv

PROJECT = Path(r"D:\Projects\institutional-financial-ai-platform")

ALIASES = {
    "timestamp": {"timestamp", "time", "t", "quote_timestamp"},
    "symbol": {"symbol", "ticker", "s"},
    "bid_price": {"bid_price", "bid", "bp"},
    "ask_price": {"ask_price", "ask", "ap"},
    "bid_size": {"bid_size", "bidsize", "bs"},
    "ask_size": {"ask_size", "asksize", "as"},
}

SKIP = {".venv", ".git", "__pycache__", "node_modules"}


def mapping_for(columns):
    normalized = {str(column).strip().lower(): column for column in columns}
    mapping = {}

    for required, aliases in ALIASES.items():
        match = next(
            (normalized[alias] for alias in aliases if alias in normalized),
            None,
        )
        if match is None:
            return None
        mapping[required] = match

    return mapping


def excluded(path):
    return any(part.lower() in SKIP for part in path.parts)


matches = []

for path in PROJECT.rglob("*.csv"):
    if excluded(path):
        continue

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            columns = next(csv.reader(handle), [])

        mapping = mapping_for(columns)
        if mapping:
            matches.append((path, "CSV", mapping))
    except Exception:
        pass


try:
    import pyarrow.parquet as pq

    for path in PROJECT.rglob("*.parquet"):
        if excluded(path):
            continue

        try:
            columns = pq.read_schema(path).names
            mapping = mapping_for(columns)

            if mapping:
                matches.append((path, "PARQUET", mapping))
        except Exception:
            pass
except ImportError:
    print("PyArrow unavailable; Parquet files were not scanned.")


if not matches:
    print("")
    print("NO HISTORICAL QUOTE SOURCES FOUND")
    print("The project does not contain all required quote fields.")
else:
    print("")
    print("HISTORICAL QUOTE SOURCES FOUND:")

    for path, file_type, mapping in matches:
        print("")
        print(f"Type: {file_type}")
        print(f"Path: {path}")
        print(f"Columns: {mapping}")
