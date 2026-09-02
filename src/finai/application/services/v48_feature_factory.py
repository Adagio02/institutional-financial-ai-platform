from __future__ import annotations

from finai.application.services.v48_feature_service import V48FeatureService
from finai.core.config import Settings


def build_v48_feature_service(*, settings: Settings) -> V48FeatureService:
    del settings
    return V48FeatureService()
