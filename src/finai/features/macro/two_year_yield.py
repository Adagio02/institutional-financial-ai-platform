"""FRED macro feature for DGS2."""
SERIES_ID = "DGS2"

def metadata() -> dict[str, str]:
    return {"name": "two_year_yield", "series_id": SERIES_ID}
