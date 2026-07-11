"""FastAPI runtime entrypoint for NexoMercado AI."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.analyses import router as analyses_router
from app.api.v1.briefings import router as briefings_router
from app.api.v1.events import router as events_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.signals import router as signals_router


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
    async def handle_not_found(_: Request, exc: KeyError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def handle_conflict(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return app


app = create_app()
