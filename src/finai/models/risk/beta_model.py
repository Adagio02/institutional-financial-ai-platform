"""Model component: risk.beta_model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "beta_model"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "risk", "component": "beta_model", "status": "implementation scaffold"}
