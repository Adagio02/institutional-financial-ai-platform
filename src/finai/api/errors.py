from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, object] | None = None


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    request_id = getattr(
        request.state,
        "request_id",
        request.headers.get("X-Request-ID"),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )