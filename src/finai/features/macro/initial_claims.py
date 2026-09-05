"""FRED macro feature for ICSA."""

SERIES_ID = "ICSA"


def metadata() -> dict[str, str]:
    return {"name": "initial_claims", "series_id": SERIES_ID}
