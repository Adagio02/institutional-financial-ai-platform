"""FRED macro feature for BAA10Y."""

SERIES_ID = "BAA10Y"


def metadata() -> dict[str, str]:
    return {"name": "credit_spread", "series_id": SERIES_ID}
