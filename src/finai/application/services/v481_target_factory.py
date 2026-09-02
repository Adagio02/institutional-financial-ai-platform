from __future__ import annotations

from finai.application.services.v481_target_service import V481TargetService
from finai.core.config import Settings


def build_v481_target_service(*, settings: Settings) -> V481TargetService:
    del settings
    return V481TargetService()
