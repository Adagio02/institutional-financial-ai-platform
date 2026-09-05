from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import UUID

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.strategy_attribution import (
    StrategyAttributionModel,
)


class StrategyAttributionRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        instrument_id: UUID,
        order_id: UUID,
        fill_id: UUID | None,
        symbol: str,
        notional: float,
        realized_pnl_delta: float,
        commission: float,
    ) -> StrategyAttributionModel:
        net_pnl_delta = realized_pnl_delta - commission

        model = StrategyAttributionModel(
            account_id=account_id,
            strategy_key=strategy_key,
            instrument_id=instrument_id,
            order_id=order_id,
            fill_id=fill_id,
            symbol=symbol,
            notional=notional,
            realized_pnl_delta=(realized_pnl_delta),
            commission=commission,
            net_pnl_delta=(net_pnl_delta),
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def daily_net_pnl(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        now: datetime | None = None,
    ) -> float:
        current_time = now or datetime.now(UTC)

        start = current_time.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        end = start + timedelta(days=1)

        statement = select(
            func.coalesce(
                func.sum(StrategyAttributionModel.net_pnl_delta),
                0.0,
            )
        ).where(
            StrategyAttributionModel.account_id == account_id,
            StrategyAttributionModel.strategy_key == strategy_key,
            StrategyAttributionModel.created_at >= start,
            StrategyAttributionModel.created_at < end,
        )

        result = self._session.scalar(statement)

        return float(result or 0.0)
