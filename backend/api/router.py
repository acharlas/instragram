"""Top-level API router composition."""

from fastapi import APIRouter

from .v1 import router as v1_router

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router, prefix="/v1")
