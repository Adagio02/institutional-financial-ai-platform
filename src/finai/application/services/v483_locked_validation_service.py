from __future__ import annotations

from finai.application.services.v483_ic_service import V483ICAnalysisService


class V483LockedValidationService(V483ICAnalysisService):
    """Legacy import alias for V4.8.3 IC analysis.

    This class never opens locked validation. Locked validation is V5.6 in the
    project roadmap.
    """
