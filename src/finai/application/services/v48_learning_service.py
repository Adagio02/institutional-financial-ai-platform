from __future__ import annotations

from typing import Any

from finai.application.services.v48_feature_service import V48FeatureService


class V48LearningService(V48FeatureService):
    """Backward-compatible facade for the corrected V4.8 feature platform."""

    def audit_dataset(self) -> dict[str, Any]:
        return self.run()

    def run_discovery(self) -> dict[str, Any]:
        return self.run()
