"""Model component: volatility.ewma."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "ewma"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "volatility", "component": "ewma", "status": "implementation scaffold"}
