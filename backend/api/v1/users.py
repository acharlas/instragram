"""User profile endpoints."""

from __future__ import annotations

from io import BytesIO
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from core import settings
from models import Follow, User
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


@router.post("/users/{username}/follow", status_code=status.HTTP_200_OK)
async def follow_user(
    username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if username == current_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")

    result = await session.execute(select(User).where(User.username == username))
    followee = result.scalar_one_or_none()
    if followee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await session.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.followee_id == followee.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return {"detail": "Already following"}

    follow = Follow(follower_id=current_user.id, followee_id=followee.id)
    session.add(follow)
    await session.commit()
    return {"detail": "Followed"}


@router.delete("/users/{username}/follow", status_code=status.HTTP_200_OK)
async def unfollow_user(
    username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await session.execute(select(User).where(User.username == username))
    followee = result.scalar_one_or_none()
    if followee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await session.execute(
        delete(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.followee_id == followee.id,
        )
    )
    await session.commit()
    return {"detail": "Unfollowed"}


@router.get("/users/{username}/followers", response_model=list[UserProfilePublic])
async def list_followers(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> list[UserProfilePublic]:
    result = await session.execute(select(User).where(User.username == username))
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    followers_query = (
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.followee_id == target_user.id)
        .order_by(User.username)
    )
    followers_result = await session.execute(followers_query)
    followers = followers_result.scalars().all()
    return [UserProfilePublic.model_validate(user) for user in followers]


@router.get("/users/{username}/following", response_model=list[UserProfilePublic])
async def list_following(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> list[UserProfilePublic]:
    result = await session.execute(select(User).where(User.username == username))
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    following_query = (
        select(User)
        .join(Follow, Follow.followee_id == User.id)
        .where(Follow.follower_id == target_user.id)
        .order_by(User.username)
    )
    following_result = await session.execute(following_query)
    following = following_result.scalars().all()
    return [UserProfilePublic.model_validate(user) for user in following]
