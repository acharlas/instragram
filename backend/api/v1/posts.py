"""Post creation and retrieval endpoints."""

from __future__ import annotations

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
from models import Post, User
from services import ensure_bucket, get_minio_client, process_image_bytes

router = APIRouter(prefix="/posts", tags=["posts"])


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: str
    image_key: str
    caption: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PostResponse)
async def create_post(
    image: UploadFile = File(...),
    caption: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostResponse:
    data = await image.read()
    try:
        processed_bytes, content_type = process_image_bytes(data)
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
    return PostResponse.model_validate(post)


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
    return [PostResponse.model_validate(post) for post in posts]


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostResponse:
    result = await session.execute(
        select(Post).where(
            _eq(Post.id, post_id),
            _eq(Post.author_id, current_user.id),
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return PostResponse.model_validate(post)
