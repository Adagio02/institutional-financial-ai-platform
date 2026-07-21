"""Model component: alpha.hyperparameter_search."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "hyperparameter_search"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "alpha", "component": "hyperparameter_search", "status": "implementation scaffold"}
