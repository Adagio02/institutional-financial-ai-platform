"""Model component: volatility.evaluation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "evaluation"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "volatility", "component": "evaluation", "status": "implementation scaffold"}
