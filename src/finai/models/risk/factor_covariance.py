"""Model component: risk.factor_covariance."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "factor_covariance"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "risk", "component": "factor_covariance", "status": "implementation scaffold"}
