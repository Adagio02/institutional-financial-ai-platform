"""Model component: alpha.model_card."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "model_card"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "alpha", "component": "model_card", "status": "implementation scaffold"}
