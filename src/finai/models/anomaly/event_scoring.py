"""Model component: anomaly.event_scoring."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "event_scoring"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "anomaly", "component": "event_scoring", "status": "implementation scaffold"}
