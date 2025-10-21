"""API v1 placeholder routes."""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["v1"])


@router.get("/health", tags=["health"], summary="Readiness probe")
async def readiness_probe() -> dict[str, str]:
    """Return a simple payload that signals API availability."""
    return {
        "status": "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


# Future routers will be included here, for example:
# from .endpoints import auth, users, posts
# router.include_router(auth.router, prefix="/auth", tags=["auth"])
