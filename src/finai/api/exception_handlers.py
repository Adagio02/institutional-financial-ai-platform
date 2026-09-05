from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from finai.core.exceptions import (
    ConflictError,
    ProviderError,
    ResourceNotFoundError,
)


def register_exception_handlers(
    application: FastAPI,
) -> None:
    @application.exception_handler(ResourceNotFoundError)
    async def handle_resource_not_found(
        _request: Request,
        error: ResourceNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": "resource_not_found",
                "detail": str(error),
            },
        )

    @application.exception_handler(ConflictError)
    async def handle_conflict(
        _request: Request,
        error: ConflictError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": "conflict",
                "detail": str(error),
            },
        )

    @application.exception_handler(ProviderError)
    async def handle_provider_error(
        _request: Request,
        error: ProviderError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "error": "market_data_provider_error",
                "detail": str(error),
            },
        )
