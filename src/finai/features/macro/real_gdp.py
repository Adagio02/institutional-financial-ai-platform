"""FRED macro feature for GDPC1."""

SERIES_ID = "GDPC1"


def metadata() -> dict[str, str]:
    return {"name": "real_gdp", "series_id": SERIES_ID}
