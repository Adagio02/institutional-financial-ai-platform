"""FRED macro feature for T10YIE."""
SERIES_ID = "T10YIE"

def metadata() -> dict[str, str]:
    return {"name": "breakeven_inflation", "series_id": SERIES_ID}
