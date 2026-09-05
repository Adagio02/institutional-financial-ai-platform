"""FRED macro feature for CPIAUCSL."""

SERIES_ID = "CPIAUCSL"


def metadata() -> dict[str, str]:
    return {"name": "cpi", "series_id": SERIES_ID}
