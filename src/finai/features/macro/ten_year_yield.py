"""FRED macro feature for DGS10."""
SERIES_ID = "DGS10"

def metadata() -> dict[str, str]:
    return {"name": "ten_year_yield", "series_id": SERIES_ID}
