"""Model component: anomaly.robust_zscore."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "robust_zscore"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "anomaly", "component": "robust_zscore", "status": "implementation scaffold"}
