"""Tests for the home feed endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from models import Follow, Post, User
from api.v1 import feed as feed_api


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)


def make_user_payload(prefix: str) -> dict[str, str]:
    suffix = uuid4().hex[:6]
    return {
        "username": f"{prefix}_{suffix}",
        "email": f"{prefix}_{suffix}@example.com",
        "password": "Sup3rSecret!",
    }


@pytest.mark.asyncio
async def test_home_feed_returns_followee_posts(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    viewer_payload = make_user_payload("viewer")
    followee_payload = make_user_payload("followee")

    await async_client.post("/api/v1/auth/register", json=viewer_payload)
    await async_client.post("/api/v1/auth/register", json=followee_payload)

    await async_client.post(
        "/api/v1/auth/login",
        json={"username": viewer_payload["username"], "password": viewer_payload["password"]},
    )

    viewer_result = await db_session.execute(
        select(User).where(_eq(User.username, viewer_payload["username"]))
    )
    followee_result = await db_session.execute(
        select(User).where(_eq(User.username, followee_payload["username"]))
    )
    viewer = viewer_result.scalar_one()
    followee = followee_result.scalar_one()

    db_session.add(Follow(follower_id=viewer.id, followee_id=followee.id))

    now = datetime.now(timezone.utc)
    for offset in range(3):
        db_session.add(
            Post(
                author_id=followee.id,
                image_key=f"feed/{offset}.jpg",
                caption=f"Post {offset}",
                created_at=now - timedelta(minutes=offset),
                updated_at=now - timedelta(minutes=offset),
            )
        )
    await db_session.commit()

    response = await async_client.get("/api/v1/feed/home")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    captions = [item["caption"] for item in body]
    assert captions == ["Post 0", "Post 1", "Post 2"]


@pytest.mark.asyncio
async def test_home_feed_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/feed/home")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_home_feed_missing_user_id_raises(db_session: AsyncSession):
    user = User(
        username="broken_user",
        email="broken@example.com",
        password_hash="hash",
    )
    user.id = None  # type: ignore[assignment]

    with pytest.raises(HTTPException):
        await feed_api.home_feed(session=db_session, current_user=user)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_home_feed_direct_call_returns_posts(db_session: AsyncSession):
    user = User(
        id="user-direct",
        username="direct_user",
        email="direct@example.com",
        password_hash="hash",
    )
    followee = User(
        id="followee-direct",
        username="direct_followee",
        email="direct_followee@example.com",
        password_hash="hash",
    )
    db_session.add_all([user, followee])
    await db_session.commit()

    db_session.add(Follow(follower_id=user.id, followee_id=followee.id))
    db_session.add(
        Post(
            author_id=followee.id,
            image_key="direct/key.jpg",
            caption="Direct",
        )
    )
    await db_session.commit()

    result = await feed_api.home_feed(session=db_session, current_user=user)
    assert len(result) == 1
    assert result[0].caption == "Direct"
