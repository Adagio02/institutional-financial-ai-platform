from fastapi import APIRouter

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/{ticker}")
def market(ticker: str) -> dict[str, object]:
    return {"ticker": ticker.upper(), "status": "connect_gold_market_snapshot"}
