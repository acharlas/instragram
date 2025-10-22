"""Authentication endpoints."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from core import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    settings,
    verify_password,
)
from models import RefreshToken, User

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
COOKIE_PATH = "/"
COOKIE_SAMESITE = "lax"
COOKIE_SECURE = settings.app_env != "local"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=80)
    bio: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    name: str | None = None
    bio: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _access_token_ttl() -> timedelta:
    return timedelta(minutes=settings.access_token_expire_minutes)


def _refresh_token_ttl() -> timedelta:
    return timedelta(minutes=settings.refresh_token_expire_minutes)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _store_refresh_token(
    session: AsyncSession,
    user_id: int,
    token: str,
) -> RefreshToken:
    payload = decode_token(token)
    token_obj = RefreshToken(
        user_id=user_id,
        token_hash=_hash_refresh_token(token),
        issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )
    session.add(token_obj)
    return token_obj


async def _get_refresh_token(
    session: AsyncSession,
    token: str,
) -> RefreshToken:
    hashed = _hash_refresh_token(token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hashed)
    )
    token_obj = result.scalar_one_or_none()
    if token_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if token_obj.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked",
        )
    if _ensure_aware(token_obj.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )
    return token_obj


def _set_token_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    access_max_age = int(_access_token_ttl().total_seconds())
    refresh_max_age = int(_refresh_token_ttl().total_seconds())

    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=access_max_age,
        path=COOKIE_PATH,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=refresh_max_age,
        path=COOKIE_PATH,
    )


def _clear_token_cookies(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_COOKIE,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    existing = await session.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that username or email already exists",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        bio=payload.bio,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await session.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    await _store_refresh_token(session, user.id, refresh_token)
    await session.commit()

    _set_token_cookies(response, access_token, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    token_obj = await _get_refresh_token(session, refresh_token)
    user_id = int(payload["sub"])

    now = datetime.now(timezone.utc)
    token_obj.revoked_at = now

    access_token = create_access_token(str(user_id))
    new_refresh_token = create_refresh_token(str(user_id))
    await _store_refresh_token(session, user_id, new_refresh_token)
    await session.commit()

    _set_token_cookies(response, access_token, new_refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if refresh_token:
        hashed = _hash_refresh_token(refresh_token)
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hashed)
        )
        token_obj = result.scalar_one_or_none()
        if token_obj and token_obj.revoked_at is None:
            token_obj.revoked_at = datetime.now(timezone.utc)
        await session.commit()

    _clear_token_cookies(response)
    return {"detail": "Logged out"}
