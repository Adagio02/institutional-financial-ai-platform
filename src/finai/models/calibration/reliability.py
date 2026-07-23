"""Model component: calibration.reliability."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "reliability"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "calibration", "component": "reliability", "status": "implementation scaffold"}
