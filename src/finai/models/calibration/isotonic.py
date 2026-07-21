"""Model component: calibration.isotonic."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "isotonic"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "calibration", "component": "isotonic", "status": "implementation scaffold"}
