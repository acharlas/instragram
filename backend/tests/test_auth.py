"""End-to-end tests for authentication endpoints."""

import hashlib
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from api.v1.auth import MAX_ACTIVE_REFRESH_TOKENS
from models import RefreshToken, User


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)

def build_payload() -> dict[str, str | None]:
    suffix = uuid4().hex[:8]
    return {
        "username": f"alice_{suffix}",
        "email": f"alice_{suffix}@example.com",
        "password": "Sup3rSecret!",
        "name": "Alice",
        "bio": "Hello, world!",
    }


@pytest.mark.asyncio
async def test_register_creates_user(async_client, db_session: AsyncSession):
    payload = build_payload()
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]

    result = await db_session.execute(
        select(User).where(_eq(User.username, payload["username"]))
    )
    user = result.scalar_one()
    assert user.password_hash != payload["password"]


@pytest.mark.asyncio
async def test_register_conflict(async_client):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_sets_tokens(async_client, db_session: AsyncSession):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]

    assert response.cookies.get("access_token") == data["access_token"]
    assert response.cookies.get("refresh_token") == data["refresh_token"]

    result = await db_session.execute(select(RefreshToken))
    tokens = result.scalars().all()
    assert len(tokens) == 1


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(async_client, db_session: AsyncSession):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    old_refresh = login_response.json()["refresh_token"]

    refresh_response = await async_client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["refresh_token"]

    assert new_refresh != old_refresh

    hashed_old = hashlib.sha256(old_refresh.encode()).hexdigest()
    result = await db_session.execute(
        select(RefreshToken).where(_eq(RefreshToken.token_hash, hashed_old))
    )
    stored = result.scalar_one()
    assert stored.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(async_client, db_session: AsyncSession):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = await async_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    set_cookie_header = "; ".join(logout_response.headers.get_list("set-cookie"))
    assert 'refresh_token=""' in set_cookie_header
    assert 'access_token=""' in set_cookie_header

    hashed = hashlib.sha256(refresh_token.encode()).hexdigest()
    result = await db_session.execute(
        select(RefreshToken).where(_eq(RefreshToken.token_hash, hashed))
    )
    token = result.scalar_one()
    assert token.revoked_at is not None


@pytest.mark.asyncio
async def test_refresh_token_store_limits_active_tokens(async_client, db_session: AsyncSession):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    login_payload = {"username": payload["username"], "password": payload["password"]}
    for _ in range(MAX_ACTIVE_REFRESH_TOKENS + 3):
        response = await async_client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200

    user_result = await db_session.execute(
        select(User).where(_eq(User.username, payload["username"]))
    )
    user = user_result.scalar_one()

    tokens_result = await db_session.execute(
        select(RefreshToken)
        .where(_eq(RefreshToken.user_id, user.id))
        .order_by(RefreshToken.issued_at.desc())
    )
    tokens = tokens_result.scalars().all()

    assert len(tokens) == MAX_ACTIVE_REFRESH_TOKENS
