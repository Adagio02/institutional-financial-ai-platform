"""Model component: volatility.historical."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "historical"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "volatility", "component": "historical", "status": "implementation scaffold"}
