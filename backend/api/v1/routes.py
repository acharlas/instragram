"""API v1 routes."""

from datetime import datetime, timezone

from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .posts import router as posts_router
from .feed import router as feed_router

router = APIRouter(tags=["v1"])
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(posts_router)
router.include_router(feed_router)


@router.get("/health", tags=["health"], summary="Readiness probe")
async def readiness_probe() -> dict[str, str]:
    """Return a simple payload that signals API availability."""
    return {
        "status": "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
