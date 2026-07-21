"""Data-quality check: macro_vintage."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(name="macro_vintage", passed=True, detail="Implement dataset-specific thresholds.")
