"""FRED macro feature for VIXCLS."""
SERIES_ID = "VIXCLS"

def metadata() -> dict[str, str]:
    return {"name": "vix", "series_id": SERIES_ID}
