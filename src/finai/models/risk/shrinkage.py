"""Model component: risk.shrinkage."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "shrinkage"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "risk", "component": "shrinkage", "status": "implementation scaffold"}
