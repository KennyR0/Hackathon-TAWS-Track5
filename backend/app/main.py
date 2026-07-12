"""FastAPI runtime entrypoint for NexoMercado AI."""

from __future__ import annotations

from fastapi import HTTPException
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.analyses import router as analyses_router
from app.api.v1.briefings import router as briefings_router
from app.api.v1.events import router as events_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.signals import router as signals_router
from app.contracts.api import ApiError


def _api_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    payload_data: dict[str, object] = {"code": code, "message": message}
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        try:
            ApiError.model_validate({"code": code, "message": message, "requestId": request_id})
            payload_data["requestId"] = request_id
        except Exception:
            pass
    payload = ApiError.model_validate(payload_data)
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="NexoMercado AI API",
        version="0.1.0",
        description="Backend runtime para el MVP fixtures-first del Track 5.",
    )
    app.include_router(health_router)
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(signals_router, prefix="/api/v1")
    app.include_router(reviews_router, prefix="/api/v1")
    app.include_router(briefings_router, prefix="/api/v1")
    app.include_router(analyses_router, prefix="/api/v1")

    @app.exception_handler(KeyError)
    async def handle_not_found(request: Request, exc: KeyError) -> JSONResponse:
        message = str(exc.args[0]) if exc.args else "Resource not found."
        return _api_error_response(
            request,
            status_code=404,
            code="not_found",
            message=message,
        )

    @app.exception_handler(ValueError)
    async def handle_conflict(request: Request, exc: ValueError) -> JSONResponse:
        return _api_error_response(
            request,
            status_code=409,
            code="conflict",
            message=str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        detail = exc.errors()[0] if exc.errors() else {"msg": "Invalid request."}
        location = " -> ".join(str(item) for item in detail.get("loc", ()))
        message = detail.get("msg", "Invalid request.")
        if location:
            message = f"{location}: {message}"
        return _api_error_response(
            request,
            status_code=422,
            code="validation_error",
            message=message,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        status_code = exc.status_code
        code = "bad_request"
        if status_code == 404:
            code = "not_found"
        elif status_code == 409:
            code = "conflict"
        elif status_code == 422:
            code = "validation_error"
        return _api_error_response(
            request,
            status_code=status_code,
            code=code,
            message=str(exc.detail),
        )

    return app


app = create_app()
