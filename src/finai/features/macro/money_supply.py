"""FRED macro feature for M2SL."""

SERIES_ID = "M2SL"


def metadata() -> dict[str, str]:
    return {"name": "money_supply", "series_id": SERIES_ID}
