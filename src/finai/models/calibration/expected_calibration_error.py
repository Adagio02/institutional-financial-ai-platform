"""Model component: calibration.expected_calibration_error."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ComponentConfig:
    name: str = "expected_calibration_error"
    enabled: bool = True

def describe() -> dict[str, object]:
    return {"group": "calibration", "component": "expected_calibration_error", "status": "implementation scaffold"}
