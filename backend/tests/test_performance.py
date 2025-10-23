"""Performance-oriented regression tests."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select

from core.security import hash_password
from models import Follow, Post, User


@pytest.mark.asyncio
async def test_follow_table_has_followee_index(db_session):
    async with db_session.bind.connect() as conn:
        indexes = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_indexes("follows")
        )
    assert any(index["name"] == "ix_follows_followee_id" for index in indexes)


@pytest.mark.asyncio
async def test_feed_query_is_fast(async_client, db_session):
    viewer_payload = {
        "username": "viewer_perf",
        "email": "viewer_perf@example.com",
        "password": "Sup3rSecret!",
    }
    await async_client.post("/api/v1/auth/register", json=viewer_payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": viewer_payload["username"],
            "password": viewer_payload["password"],
        },
    )

    viewer_result = await db_session.execute(
        select(User).where(User.username == viewer_payload["username"])
    )
    viewer = viewer_result.scalar_one()

    authors: list[User] = []
    for idx in range(10):
        author = User(
            username=f"author_perf_{idx}",
            email=f"author_perf_{idx}@example.com",
            password_hash=hash_password("Sup3rSecret!"),
        )
        db_session.add(author)
        authors.append(author)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    for author in authors:
        db_session.add(Follow(follower_id=viewer.id, followee_id=author.id))
        for offset in range(5):
            db_session.add(
                Post(
                    author_id=author.id,
                    image_key=f"perf/{author.id}/{uuid4().hex}.jpg",
                    caption="Perf",
                    created_at=now - timedelta(minutes=offset),
                    updated_at=now - timedelta(minutes=offset),
                )
            )
    await db_session.commit()

    start = time.perf_counter()
    response = await async_client.get("/api/v1/posts/feed")
    duration = time.perf_counter() - start

    assert response.status_code == 200
    assert len(response.json()) == len(authors) * 5
    assert duration < 0.5
