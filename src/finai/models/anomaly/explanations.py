"""Model component: anomaly.explanations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "explanations"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "anomaly", "component": "explanations", "status": "implementation scaffold"}
