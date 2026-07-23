"""Monitoring module: prometheus."""


def collect() -> dict[str, object]:
    return {"metric": "prometheus", "status": "not_collected"}
