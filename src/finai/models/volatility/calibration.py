"""Model component: volatility.calibration."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "calibration"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "volatility", "component": "calibration", "status": "implementation scaffold"}
