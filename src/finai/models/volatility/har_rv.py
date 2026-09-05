"""Model component: volatility.har_rv."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "har_rv"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "volatility", "component": "har_rv", "status": "implementation scaffold"}
