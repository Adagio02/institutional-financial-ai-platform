"""Model component: risk.factor_exposures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "factor_exposures"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "risk", "component": "factor_exposures", "status": "implementation scaffold"}
