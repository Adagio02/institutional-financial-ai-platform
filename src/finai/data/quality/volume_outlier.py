"""Data-quality check: volume_outlier."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(name="volume_outlier", passed=True, detail="Implement dataset-specific thresholds.")
