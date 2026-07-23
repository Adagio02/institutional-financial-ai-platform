"""FRED macro feature for DFF."""

SERIES_ID = "DFF"


def metadata() -> dict[str, str]:
    return {"name": "fed_funds", "series_id": SERIES_ID}
