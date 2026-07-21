"""Model component: volatility.garch_bridge."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "garch_bridge"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "volatility", "component": "garch_bridge", "status": "implementation scaffold"}
