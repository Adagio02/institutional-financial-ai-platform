"""Model component: risk.risk_report."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "risk_report"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "risk", "component": "risk_report", "status": "implementation scaffold"}
