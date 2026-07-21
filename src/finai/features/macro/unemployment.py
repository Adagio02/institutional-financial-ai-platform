"""FRED macro feature for UNRATE."""
SERIES_ID = "UNRATE"

def metadata() -> dict[str, str]:
    return {"name": "unemployment", "series_id": SERIES_ID}
