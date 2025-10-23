"""Tests for the Redis-backed rate limiter middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from services import RateLimiter, set_rate_limiter


class InMemoryRedis:
    def __init__(self) -> None:
        self.data: dict[str, int] = {}

    async def incr(self, key: str) -> int:  # pragma: no cover - simple helper
        value = self.data.get(key, 0) + 1
        self.data[key] = value
        return value

    async def expire(self, key: str, ttl: int) -> None:  # pragma: no cover - noop
        return None


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_threshold(
    async_client: AsyncClient, app: FastAPI
) -> None:
    limiter = RateLimiter(InMemoryRedis(), limit=2, window_seconds=60)
    app.state.rate_limiter_override = limiter

    try:
        first = await async_client.get("/api/v1/health")
        assert first.status_code == 200

        second = await async_client.get("/api/v1/health")
        assert second.status_code == 200

        third = await async_client.get("/api/v1/health")
        assert third.status_code == 429
        assert third.json()["detail"] == "Too Many Requests"
    finally:
        if hasattr(app.state, "rate_limiter_override"):
            del app.state.rate_limiter_override
        set_rate_limiter(None)


@pytest.mark.asyncio
async def test_rate_limiter_can_be_disabled(async_client: AsyncClient, app: FastAPI) -> None:
    limiter = RateLimiter(InMemoryRedis(), limit=0, window_seconds=60)
    app.state.rate_limiter_override = limiter

    try:
        for _ in range(5):
            response = await async_client.get("/api/v1/health")
            assert response.status_code == 200
    finally:
        if hasattr(app.state, "rate_limiter_override"):
            del app.state.rate_limiter_override

    set_rate_limiter(None)
