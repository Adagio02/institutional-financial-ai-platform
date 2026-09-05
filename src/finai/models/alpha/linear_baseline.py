"""Model component: alpha.linear_baseline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "linear_baseline"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "alpha", "component": "linear_baseline", "status": "implementation scaffold"}
