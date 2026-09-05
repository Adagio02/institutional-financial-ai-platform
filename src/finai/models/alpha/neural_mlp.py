"""Model component: alpha.neural_mlp."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "neural_mlp"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "alpha", "component": "neural_mlp", "status": "implementation scaffold"}
