from uuid import UUID

from sqlalchemy.orm import Session

from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)


class PortfolioService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._account_repository = PaperAccountRepository(session)

        self._position_repository = PaperPositionRepository(session)

    def summarize(
        self,
        *,
        account_id: UUID,
        prices: dict[str, float] | None = None,
    ) -> dict:
        account = self._account_repository.get_by_id(account_id)

        if account is None:
            raise LookupError(f"Paper account not found: {account_id}")

        positions = self._position_repository.list_for_account(account_id)

        prices = prices or {}

        gross_exposure = 0.0
        net_exposure = 0.0
        unrealized_pnl = 0.0

        position_rows = []

        for position in positions:
            market_price = prices.get(
                position.symbol,
                position.average_price,
            )

            market_value = position.quantity * market_price

            position_unrealized_pnl = (market_price - position.average_price) * position.quantity

            gross_exposure += abs(market_value)

            net_exposure += market_value

            unrealized_pnl += position_unrealized_pnl

            position_rows.append(
                {
                    "instrument_id": (position.instrument_id),
                    "symbol": position.symbol,
                    "quantity": (position.quantity),
                    "average_price": (position.average_price),
                    "market_price": (market_price),
                    "market_value": (market_value),
                    "unrealized_pnl": (position_unrealized_pnl),
                }
            )

        equity = account.cash + net_exposure

        return {
            "account_id": account.id,
            "cash": account.cash,
            "gross_exposure": gross_exposure,
            "net_exposure": net_exposure,
            "equity": equity,
            "realized_pnl": (account.realized_pnl),
            "unrealized_pnl": (unrealized_pnl),
            "positions": position_rows,
        }
