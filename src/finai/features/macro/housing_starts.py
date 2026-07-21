"""FRED macro feature for HOUST."""
SERIES_ID = "HOUST"

def metadata() -> dict[str, str]:
    return {"name": "housing_starts", "series_id": SERIES_ID}
