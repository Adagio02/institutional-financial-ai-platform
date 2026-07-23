"""Model component: anomaly.isolation_forest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "isolation_forest"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {
        "group": "anomaly",
        "component": "isolation_forest",
        "status": "implementation scaffold",
    }
