from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/live")
def live_health() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
def ready_health() -> dict[str, str]:
    return {"status": "ready"}
