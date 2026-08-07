"""Post visibility and interaction access policy checks."""

from __future__ import annotations

from typing import cast

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from db.query_helpers import _eq
from models import Follow, Post, User
from services.account_privacy import can_view_account_content
from services.account_blocks import build_not_blocked_either_direction_filter


def build_author_view_filter(
    *,
    viewer_id: str,
    post_author_column: ColumnElement[str],
    author_is_private_column: ColumnElement[bool],
) -> ColumnElement[bool]:
    """Return a SQL predicate for authors whose posts are visible to viewer."""
    follow_exists = exists(
        select(1)
        .where(
            _eq(Follow.follower_id, viewer_id),
            _eq(Follow.followee_id, post_author_column),
        )
        # ponytail: keep Follow in the subquery even when the outer query
        # already joins Follow (follower lists) — auto-correlation would
        # strip the subquery's FROM entirely.
        .correlate()
    )
    return cast(
        ColumnElement[bool],
        and_(
            build_not_blocked_either_direction_filter(
                viewer_id=viewer_id,
                candidate_user_id_column=post_author_column,
            ),
            or_(
                _eq(post_author_column, viewer_id),
                cast(ColumnElement[bool], author_is_private_column.is_(False)),
                follow_exists,
            ),
        ),
    )


async def require_post_view_access(
    session: AsyncSession,
    *,
    viewer_id: str,
    post_id: int | None = None,
    post_author_id: str | None = None,
) -> str:
    """Return post author id when viewer can view; otherwise raise 404."""
    resolved_author_id = post_author_id
    if resolved_author_id is None:
        if post_id is None:
            raise ValueError("post_id is required when post_author_id is not provided")
        resolved_author_id = await require_post_exists(session, post_id)

    author_result = await session.execute(
        select(User).where(_eq(User.id, resolved_author_id))
    )
    author = author_result.scalar_one_or_none()
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    can_view = await can_view_account_content(
        session,
        viewer_id=viewer_id,
        account=author,
    )
    if not can_view:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return resolved_author_id


async def require_post_exists(
    session: AsyncSession,
    post_id: int,
) -> str:
    """Return the post author id or raise 404 when the post does not exist."""
    post_author_column = cast(ColumnElement[str], Post.author_id)
    result = await session.execute(
        select(post_author_column)
        .where(_eq(Post.id, post_id))
        .limit(1)
    )
    author_id = result.scalar_one_or_none()
    if author_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return author_id


async def require_post_interaction_access(
    session: AsyncSession,
    *,
    viewer_id: str,
    post_id: int,
) -> str:
    """Return the post author id when viewer can interact; otherwise raise 404."""
    post_author_column = cast(ColumnElement[str], Post.author_id)
    follow_exists = exists(
        select(1).where(
            _eq(Follow.follower_id, viewer_id),
            _eq(Follow.followee_id, post_author_column),
        )
    )
    result = await session.execute(
        select(post_author_column)
        .where(
            _eq(Post.id, post_id),
            build_not_blocked_either_direction_filter(
                viewer_id=viewer_id,
                candidate_user_id_column=post_author_column,
            ),
            or_(_eq(post_author_column, viewer_id), follow_exists),
        )
        .limit(1)
    )
    author_id = result.scalar_one_or_none()
    if author_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return author_id
