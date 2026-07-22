from __future__ import annotations

from fastapi import APIRouter, Response, status

from finai.api.schemas.health import (
    LivenessResponse,
    ReadinessDependency,
    ReadinessResponse,
)
from finai.core.config import get_settings
from finai.infrastructure.database.engine import check_database_connection


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get(
    "/live",
    response_model=LivenessResponse,
)
def liveness() -> LivenessResponse:
    settings = get_settings()

    return LivenessResponse(
        status="alive",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
)
def readiness(response: Response) -> ReadinessResponse:
    settings = get_settings()
    database_ready = check_database_connection()

    dependencies = [
        ReadinessDependency(
            name="postgresql",
            ready=database_ready,
            detail=None if database_ready else "Database connection failed",
        )
    ]

    is_ready = all(dependency.ready for dependency in dependencies)

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        service=settings.app_name,
        version=settings.app_version,
        dependencies=dependencies,
    )