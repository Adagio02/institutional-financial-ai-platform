"""FRED macro feature for PCE."""

SERIES_ID = "PCE"


def metadata() -> dict[str, str]:
    return {"name": "pce", "series_id": SERIES_ID}
