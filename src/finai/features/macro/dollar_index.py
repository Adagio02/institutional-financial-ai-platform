"""FRED macro feature for DTWEXBGS."""
SERIES_ID = "DTWEXBGS"

def metadata() -> dict[str, str]:
    return {"name": "dollar_index", "series_id": SERIES_ID}
