from fastapi import APIRouter

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("")
def quality() -> dict[str, object]:
    return {"status": "not_run", "checks": []}
