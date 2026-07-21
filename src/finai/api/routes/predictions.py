from fastapi import APIRouter
router = APIRouter(prefix="/predictions", tags=["predictions"])
@router.get("/{ticker}")
def predictions(ticker: str) -> dict[str, object]:
    return {"ticker": ticker.upper(), "model": "cross_sectional_alpha", "status": "not_scored"}
