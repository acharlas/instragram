"""Common FastAPI dependencies."""

from collections.abc import AsyncGenerator
from typing import Any, cast

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from core import decode_token
from db.session import get_session
from models import User

ACCESS_COOKIE_NAME = "access_token"


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency alias for database access."""
    async for session in get_session():
        yield session


async def get_current_user(
    request: Request, session: AsyncSession = Depends(get_db)
) -> User:
    """Return the authenticated user from the access token cookie."""
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_token(token)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id_raw = payload.get("sub")
    if isinstance(user_id_raw, (str, int)):
        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            ) from None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await session.execute(select(User).where(_eq(User.id, user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
