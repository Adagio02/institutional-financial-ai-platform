"""Model component: risk.specific_risk."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "specific_risk"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "risk", "component": "specific_risk", "status": "implementation scaffold"}
