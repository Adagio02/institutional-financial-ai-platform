from fastapi import APIRouter
router = APIRouter(prefix="/portfolio", tags=["portfolio"])
@router.post("/optimize")
def optimize(payload: dict) -> dict[str, object]:
    return {"status": "accepted", "constraints": payload}
