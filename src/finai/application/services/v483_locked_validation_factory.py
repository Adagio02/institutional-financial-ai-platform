from __future__ import annotations

from finai.application.services.v483_locked_validation_service import V483LockedValidationService
from finai.core.config import Settings


def build_v483_locked_validation_service(*, settings: Settings) -> V483LockedValidationService:
    del settings
    return V483LockedValidationService()
