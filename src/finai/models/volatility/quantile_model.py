"""Model component: volatility.quantile_model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "quantile_model"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {
        "group": "volatility",
        "component": "quantile_model",
        "status": "implementation scaffold",
    }
