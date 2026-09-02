from __future__ import annotations

from finai.application.services.v483_ic_service import V483ICAnalysisService
from finai.core.config import Settings


def build_v483_ic_service(*, settings: Settings) -> V483ICAnalysisService:
    del settings
    return V483ICAnalysisService()
