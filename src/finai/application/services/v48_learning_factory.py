from __future__ import annotations

from finai.application.services.v48_learning_service import V48LearningService
from finai.core.config import Settings


def build_v48_learning_service(*, settings: Settings) -> V48LearningService:
    del settings
    return V48LearningService()
