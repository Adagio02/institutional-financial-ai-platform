"""Model component: risk.portfolio_variance."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "portfolio_variance"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "risk", "component": "portfolio_variance", "status": "implementation scaffold"}
