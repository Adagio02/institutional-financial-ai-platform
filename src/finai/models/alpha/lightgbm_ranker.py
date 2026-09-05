"""Model component: alpha.lightgbm_ranker."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentConfig:
    name: str = "lightgbm_ranker"
    enabled: bool = True


def describe() -> dict[str, object]:
    return {"group": "alpha", "component": "lightgbm_ranker", "status": "implementation scaffold"}
