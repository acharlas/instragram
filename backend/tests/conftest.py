"""Pytest fixtures for the Instragram backend."""

import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from api.deps import get_db
from app import create_app
from models import Comment, Follow, Like, Post, RefreshToken, User
from services import RateLimiter, set_rate_limiter


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Provide a shared event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator:
    """Create an in-memory SQLite engine for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to the test engine."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def app(session_maker) -> Iterator[FastAPI]:
    """Create the FastAPI app with a test database dependency override."""
    application = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    yield application


@pytest_asyncio.fixture()
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an HTTPX async client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def clean_database(session_maker) -> AsyncIterator[None]:
    """Clear tables before each test to guarantee isolation."""
    async with session_maker() as session:
        for model in (RefreshToken, Like, Comment, Follow, Post, User):
            await session.execute(delete(model))
        await session.commit()
    yield


@pytest_asyncio.fixture()
async def db_session(session_maker) -> AsyncIterator[AsyncSession]:
    """Provide a raw database session to tests."""
    async with session_maker() as session:
        yield session


class _InMemoryRedis:
    def __init__(self) -> None:
        self.data: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        value = self.data.get(key, 0) + 1
        self.data[key] = value
        return value

    async def expire(self, key: str, ttl: int) -> None:  # pragma: no cover - noop
        return None


@pytest.fixture(autouse=True)
def _rate_limiter_stub() -> Iterator[None]:
    limiter = RateLimiter(_InMemoryRedis(), limit=1_000, window_seconds=60)
    set_rate_limiter(limiter)
    yield
    set_rate_limiter(None)
