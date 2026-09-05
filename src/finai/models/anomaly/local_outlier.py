"""Model component: anomaly.local_outlier."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "local_outlier"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "anomaly", "component": "local_outlier", "status": "implementation scaffold"}
