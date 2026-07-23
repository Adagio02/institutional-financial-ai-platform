"""FRED macro feature for INDPRO."""

SERIES_ID = "INDPRO"


def metadata() -> dict[str, str]:
    return {"name": "industrial_production", "series_id": SERIES_ID}
