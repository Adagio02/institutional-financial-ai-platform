"""Model component: risk.risk_contribution."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "risk_contribution"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "risk", "component": "risk_contribution", "status": "implementation scaffold"}
