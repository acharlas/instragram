"""Feed-related endpoints."""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from api.deps import get_current_user, get_db
from models import Follow, Post, User
from .posts import PostResponse

router = APIRouter(prefix="/feed", tags=["feed"])


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)


@router.get("/home", response_model=list[PostResponse])
async def home_feed(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PostResponse]:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record missing identifier",
        )

    result = await session.execute(
        select(Post, User.name)
        .join(User, _eq(User.id, Post.author_id))
        .join(Follow, _eq(Follow.followee_id, Post.author_id))
        .where(_eq(Follow.follower_id, current_user.id))
        .order_by(Post.created_at.desc())  # type: ignore[attr-defined]
    )
    rows = result.all()
    return [
        PostResponse.from_post(post, author_name=author_name)
        for post, author_name in rows
    ]
