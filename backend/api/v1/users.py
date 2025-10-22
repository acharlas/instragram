"""User profile endpoints."""

from __future__ import annotations

from io import BytesIO
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from core import settings
from models import User
from services import ensure_bucket, get_minio_client

router = APIRouter(tags=["users"])


class UserProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str | None = None
    bio: str | None = None
    avatar_key: str | None = None


class UserProfilePrivate(UserProfilePublic):
    email: EmailStr


@router.get("/users/{username}", response_model=UserProfilePublic)
async def get_user_profile(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> UserProfilePublic:
    """Fetch a user's public profile."""
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserProfilePublic.model_validate(user)


@router.get("/me", response_model=UserProfilePrivate)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfilePrivate:
    """Return the authenticated user's full profile."""
    return UserProfilePrivate.model_validate(current_user)


@router.patch("/me", response_model=UserProfilePrivate)
async def update_me(
    name: str | None = Form(default=None),
    bio: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserProfilePrivate:
    """Update the authenticated user's profile."""
    updated = False

    if name is not None:
        current_user.name = name or None
        updated = True
    if bio is not None:
        current_user.bio = bio or None
        updated = True

    if avatar is not None:
        data = await avatar.read()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Avatar file cannot be empty",
            )

        extension = ""
        if avatar.filename and "." in avatar.filename:
            extension = avatar.filename.rsplit(".", 1)[1].lower()
            extension = f".{extension}"
        object_key = f"avatars/{uuid4().hex}{extension}"

        client = get_minio_client()
        ensure_bucket(client)
        client.put_object(
            settings.minio_bucket,
            object_key,
            data=BytesIO(data),
            length=len(data),
            content_type=avatar.content_type or "application/octet-stream",
        )

        current_user.avatar_key = object_key
        updated = True

    if updated:
        session.add(current_user)
        await session.commit()
        await session.refresh(current_user)

    return UserProfilePrivate.model_validate(current_user)
