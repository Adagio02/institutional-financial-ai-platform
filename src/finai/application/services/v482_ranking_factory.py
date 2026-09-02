from __future__ import annotations

from finai.application.services.v482_ranking_service import V482RankingService
from finai.core.config import Settings


def build_v482_ranking_service(*, settings: Settings) -> V482RankingService:
    return V482RankingService(
        purge_timestamps=int(getattr(settings, "v41_forward_horizon_bars", 30)),
    )
