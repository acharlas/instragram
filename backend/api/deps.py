"""Common FastAPI dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency alias for database access."""
    async for session in get_session():
        yield session
