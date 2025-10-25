"""Post creation and retrieval endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from api.deps import get_current_user, get_db
from core import settings
from models import Comment, Follow, Post, User
from services import (
    UploadTooLargeError,
    ensure_bucket,
    get_minio_client,
    process_image_bytes,
    read_upload_file,
)

router = APIRouter(prefix="/posts", tags=["posts"])


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: str
    author_name: str | None = None
    image_key: str
    caption: str | None = None

    @classmethod
    def from_post(cls, post: Post, author_name: str | None = None) -> "PostResponse":
        if post.id is None:
            raise ValueError("Post record missing identifier")
        return cls(
            id=post.id,
            author_id=post.author_id,
            author_name=author_name,
            image_key=post.image_key,
            caption=post.caption,
        )


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    author_id: str
    author_name: str | None = None
    text: str
    created_at: datetime

    @classmethod
    def from_comment(
        cls,
        comment: Comment,
        author_name: str | None = None,
    ) -> "CommentResponse":
        if comment.id is None:
            raise ValueError("Comment record missing identifier")
        return cls(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_name=author_name,
            text=comment.text,
            created_at=comment.created_at,
        )


PostResponse.model_rebuild()
CommentResponse.model_rebuild()


async def _user_can_view_post(
    session: AsyncSession,
    viewer_id: str,
    author_id: str,
) -> bool:
    if viewer_id == author_id:
        return True

    result = await session.execute(
        select(Follow)
        .where(_eq(Follow.follower_id, viewer_id), _eq(Follow.followee_id, author_id))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PostResponse)
async def create_post(
    image: UploadFile = File(...),
    caption: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostResponse:
    try:
        data = await read_upload_file(image, settings.upload_max_bytes)
        processed_bytes, content_type = process_image_bytes(data)
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record missing identifier",
        )

    object_key = f"posts/{current_user.id}/{uuid4().hex}.jpg"
    client = get_minio_client()
    ensure_bucket(client)
    client.put_object(
        settings.minio_bucket,
        object_key,
        data=BytesIO(processed_bytes),
        length=len(processed_bytes),
        content_type=content_type,
    )

    post = Post(
        author_id=current_user.id,
        image_key=object_key,
        caption=caption,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return PostResponse.from_post(post, author_name=current_user.name)


@router.get("", response_model=list[PostResponse])
async def list_posts(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PostResponse]:
    result = await session.execute(
        select(Post)
        .where(_eq(Post.author_id, current_user.id))
        .order_by(Post.created_at.desc())  # type: ignore[attr-defined]
    )
    posts = result.scalars().all()
    return [
        PostResponse.from_post(post, author_name=current_user.name)
        for post in posts
    ]


@router.get("/feed", response_model=list[PostResponse])
async def get_feed(
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


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostResponse:
    viewer_id = current_user.id
    if viewer_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record missing identifier",
        )

    result = await session.execute(
        select(Post, User.name)
        .join(User, _eq(User.id, Post.author_id))
        .where(_eq(Post.id, post_id))
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post, author_name = row

    if not await _user_can_view_post(session, viewer_id, post.author_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    return PostResponse.from_post(post, author_name=author_name)


@router.get("/{post_id}/comments", response_model=list[CommentResponse])
async def get_post_comments(
    post_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CommentResponse]:
    viewer_id = current_user.id
    if viewer_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record missing identifier",
        )

    post_author = await session.execute(
        select(Post.author_id)
        .where(_eq(Post.id, post_id))
        .limit(1)
    )
    post_author_id = post_author.scalar_one_or_none()
    if post_author_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if not await _user_can_view_post(session, viewer_id, post_author_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    result = await session.execute(
        select(Comment, User.name)
        .join(User, _eq(User.id, Comment.author_id))
        .where(_eq(Comment.post_id, post_id))
        .order_by(Comment.created_at.asc())
    )
    rows = result.all()
    return [
        CommentResponse.from_comment(comment, author_name=author_name)
        for comment, author_name in rows
    ]
