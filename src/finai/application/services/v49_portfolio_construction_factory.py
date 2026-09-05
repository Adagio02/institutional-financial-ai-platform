from __future__ import annotations

from finai.application.services.v49_portfolio_construction_service import (
    V49PortfolioConstructionService,
)
from finai.domain.portfolio.v49_construction import PortfolioConstraints


def build_v49_portfolio_construction_service(
    *, settings: object | None = None
) -> V49PortfolioConstructionService:
    del settings
    return V49PortfolioConstructionService(
        constraints=PortfolioConstraints(
            target_gross_exposure=1.0,
            target_net_exposure=0.0,
            maximum_absolute_weight=0.10,
            minimum_absolute_weight=1e-6,
        )
    )
