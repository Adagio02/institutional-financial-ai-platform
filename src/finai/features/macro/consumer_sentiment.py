"""FRED macro feature for UMCSENT."""

SERIES_ID = "UMCSENT"


def metadata() -> dict[str, str]:
    return {"name": "consumer_sentiment", "series_id": SERIES_ID}
