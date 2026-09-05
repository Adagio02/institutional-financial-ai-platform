"""Model component: alpha.random_forest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "random_forest"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "alpha", "component": "random_forest", "status": "implementation scaffold"}
