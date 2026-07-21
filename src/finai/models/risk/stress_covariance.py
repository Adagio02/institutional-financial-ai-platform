"""Model component: risk.stress_covariance."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "stress_covariance"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "risk", "component": "stress_covariance", "status": "implementation scaffold"}
