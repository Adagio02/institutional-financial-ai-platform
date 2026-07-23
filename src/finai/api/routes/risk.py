from fastapi import APIRouter

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/{ticker}")
def risk(ticker: str) -> dict[str, object]:
    return {"ticker": ticker.upper(), "risk_status": "not_scored"}
