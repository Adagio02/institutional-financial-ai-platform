"""Model component: calibration.platt."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "platt"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "calibration", "component": "platt", "status": "implementation scaffold"}
