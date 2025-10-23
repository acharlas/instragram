"""Redis-backed rate limiting utilities."""

from __future__ import annotations

import time
from functools import lru_cache
from ipaddress import ip_address, ip_network, IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Callable, Iterable, Protocol, runtime_checkable

from fastapi import status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp

from core import settings


@runtime_checkable
class SupportsRateLimitClient(Protocol):
    async def incr(self, key: str) -> int: ...

    async def expire(self, key: str, ttl: int) -> None: ...


def _parse_networks() -> tuple[IPv4Network | IPv6Network, ...]:
    networks: list[IPv4Network | IPv6Network] = []
    for cidr in settings.rate_limit_trusted_proxies:
        try:
            networks.append(ip_network(cidr, strict=False))
        except ValueError as exc:  # pragma: no cover - invalid configuration
            raise ValueError(f"Invalid CIDR in RATE_LIMIT_TRUSTED_PROXIES: {cidr}") from exc
    return tuple(networks)


@lru_cache
def _trusted_proxy_networks() -> tuple[IPv4Network | IPv6Network, ...]:
    return _parse_networks()


def _extract_client_ip_from_headers(request: Request) -> str | None:
    for header in settings.rate_limit_ip_headers:
        value = request.headers.get(header)
        if not value:
            continue
        for candidate in value.split(","):
            ip_candidate = candidate.strip()
            if not ip_candidate:
                continue
            try:
                ip_address(ip_candidate)
            except ValueError:
                continue
            return ip_candidate
    return None


def _remote_ip(request: Request) -> tuple[str | None, IPv4Address | IPv6Address | None]:
    host = request.client.host if request.client else None
    if not host:
        return None, None
    try:
        addr = ip_address(host)
    except ValueError:
        return host, None
    return host, addr


def default_client_identifier(request: Request) -> str:
    """Resolve a stable client identifier for rate limiting."""
    remote_host, remote_ip = _remote_ip(request)

    if remote_ip is not None and any(remote_ip in network for network in _trusted_proxy_networks()):
        forwarded_ip = _extract_client_ip_from_headers(request)
        if forwarded_ip:
            return forwarded_ip

    if remote_host:
        return remote_host

    return "anonymous"


class RateLimiter:
    """Simple fixed-window rate limiter backed by Redis."""

    def __init__(
        self,
        redis_client: SupportsRateLimitClient,
        limit: int,
        window_seconds: int,
        prefix: str = "rate-limit",
    ) -> None:
        self.redis = redis_client
        self.limit = max(limit, 0)
        self.window_seconds = max(window_seconds, 0)
        self.prefix = prefix

    async def allow(self, key: str) -> bool:
        """Return True when the request should be allowed, False if limited."""
        if self.limit == 0 or self.window_seconds == 0:
            return True

        bucket = int(time.time()) // self.window_seconds
        redis_key = f"{self.prefix}:{key}:{bucket}"

        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, self.window_seconds)
        return count <= self.limit


@lru_cache
def get_redis_client() -> SupportsRateLimitClient:
    """Return a cached async Redis client."""
    return Redis.from_url(settings.redis_url, decode_responses=False)


_cached_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Singleton accessor for the shared rate limiter."""
    global _cached_rate_limiter
    if _cached_rate_limiter is None:
        _cached_rate_limiter = RateLimiter(
            redis_client=get_redis_client(),
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return _cached_rate_limiter


def set_rate_limiter(limiter: RateLimiter | None) -> None:
    """Override the cached rate limiter (primarily for tests)."""
    global _cached_rate_limiter
    _cached_rate_limiter = limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that enforces the configured rate limits."""

    def __init__(
        self,
        app: ASGIApp,
        limiter_factory: Callable[[], RateLimiter],
        exempt_paths: Iterable[str] | None = None,
        exempt_prefixes: Iterable[str] | None = None,
        client_identifier: Callable[[Request], str] | None = None,
    ) -> None:
        super().__init__(app)
        self._limiter: RateLimiter | None = None
        self.limiter_factory = limiter_factory
        self.exempt_paths = set(exempt_paths or ())
        self.exempt_prefixes = tuple(exempt_prefixes or ())
        self.client_identifier = client_identifier or default_client_identifier

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.scope["type"] != "http":
            return await call_next(request)

        path = request.url.path
        if path in self.exempt_paths or any(
            path.startswith(prefix) for prefix in self.exempt_prefixes
        ):
            return await call_next(request)

        override = getattr(request.app.state, "rate_limiter_override", None)
        limiter = override if override is not None else self._get_limiter()

        if limiter is None:
            return await call_next(request)

        client_key = self.client_identifier(request) or "anonymous"
        if not await limiter.allow(client_key):
            return JSONResponse(
                {"detail": "Too Many Requests"},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return await call_next(request)

    def _get_limiter(self) -> RateLimiter | None:
        if self._limiter is None:
            try:
                self._limiter = self.limiter_factory()
            except Exception:  # pragma: no cover - defensive fallback
                self._limiter = None
        return self._limiter
