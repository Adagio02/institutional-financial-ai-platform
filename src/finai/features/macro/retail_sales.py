"""FRED macro feature for RSAFS."""
SERIES_ID = "RSAFS"

def metadata() -> dict[str, str]:
    return {"name": "retail_sales", "series_id": SERIES_ID}
