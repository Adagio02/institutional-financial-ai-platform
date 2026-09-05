from finai.application.services.v40_learning_factory import (
    create_v40_learning_service,
)
from finai.application.services.v40_shadow_service import (
    V40ShadowService,
)
from finai.core.config import (
    Settings,
)


def create_v40_shadow_service(
    *,
    settings: Settings,
) -> V40ShadowService:
    learning_service = (
        create_v40_learning_service(
            settings=settings
        )
    )

    return V40ShadowService(
        learning_service=(
            learning_service
        ),
        shadow_directory=(
            settings
            .v40_shadow_directory
        ),
        minimum_observations=(
            settings
            .v40_shadow_minimum_observations
        ),
        minimum_trades=(
            settings
            .v40_shadow_minimum_trades
        ),
        minimum_net_return=(
            settings
            .v40_shadow_minimum_net_return
        ),
        maximum_drawdown=(
            settings
            .v40_shadow_maximum_drawdown
        ),
    )