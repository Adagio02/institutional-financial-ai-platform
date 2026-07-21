"""FRED macro feature for CPILFESL."""
SERIES_ID = "CPILFESL"

def metadata() -> dict[str, str]:
    return {"name": "core_cpi", "series_id": SERIES_ID}
