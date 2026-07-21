"""FRED macro feature for DGS3MO."""
SERIES_ID = "DGS3MO"

def metadata() -> dict[str, str]:
    return {"name": "three_month_yield", "series_id": SERIES_ID}
