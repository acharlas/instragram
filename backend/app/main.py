"""FastAPI application factory and middleware wiring."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from core.config import settings
from services import RateLimitMiddleware, get_rate_limiter


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        RateLimitMiddleware,
        limiter_factory=get_rate_limiter,
        exempt_paths=("/healthz",),
        exempt_prefixes=("/docs", "/openapi.json", "/redoc"),
    )

    app.include_router(api_router)

    @app.get("/healthz", tags=["health"], summary="Liveness probe")
    async def health_probe() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
