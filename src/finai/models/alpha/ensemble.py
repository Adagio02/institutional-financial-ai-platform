"""Model component: alpha.ensemble."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "ensemble"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "alpha", "component": "ensemble", "status": "implementation scaffold"}
