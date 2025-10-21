"""SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

async_engine = create_async_engine(settings.database_url, echo=settings.debug)

AsyncSessionMaker = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionMaker() as session:
        yield session
