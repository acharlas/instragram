"""Tests for follow/unfollow endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Follow, User


def make_user_payload(prefix: str) -> dict[str, str | None]:
    suffix = uuid4().hex[:6]
    return {
        "username": f"{prefix}_{suffix}",
        "email": f"{prefix}_{suffix}@example.com",
        "password": "Sup3rSecret!",
    }


@pytest.mark.asyncio
async def test_follow_and_unfollow(async_client: AsyncClient, db_session: AsyncSession):
    follower_payload = make_user_payload("alice")
    followee_payload = make_user_payload("bob")

    await async_client.post("/api/v1/auth/register", json=follower_payload)
    await async_client.post("/api/v1/auth/register", json=followee_payload)

    await async_client.post(
        "/api/v1/auth/login",
        json={"username": follower_payload["username"], "password": follower_payload["password"]},
    )

    follow_resp = await async_client.post(f"/api/v1/users/{followee_payload['username']}/follow")
    assert follow_resp.status_code == 200
    assert follow_resp.json()["detail"] in {"Followed", "Already following"}

    result = await db_session.execute(select(Follow))
    follows = result.scalars().all()
    assert len(follows) == 1

    unfollow_resp = await async_client.delete(f"/api/v1/users/{followee_payload['username']}/follow")
    assert unfollow_resp.status_code == 200
    assert unfollow_resp.json()["detail"] == "Unfollowed"

    result = await db_session.execute(select(Follow))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_cannot_follow_self(async_client: AsyncClient):
    payload = make_user_payload("self")
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    response = await async_client.post(f"/api/v1/users/{payload['username']}/follow")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_follow_unknown_user(async_client: AsyncClient):
    payload = make_user_payload("alice")
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    response = await async_client.post("/api/v1/users/unknown_user/follow")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_followers_and_following_lists(async_client: AsyncClient):
    alice = make_user_payload("alice")
    bob = make_user_payload("bob")
    carol = make_user_payload("carol")

    for user in (alice, bob, carol):
        await async_client.post("/api/v1/auth/register", json=user)

    # Alice follows Bob and Carol
    await async_client.post("/api/v1/auth/login", json={"username": alice["username"], "password": alice["password"]})
    await async_client.post(f"/api/v1/users/{bob['username']}/follow")
    await async_client.post(f"/api/v1/users/{carol['username']}/follow")

    # Bob follows Alice
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": bob["username"], "password": bob["password"]},
    )
    await async_client.post(f"/api/v1/users/{alice['username']}/follow")

    # Check Alice followers (should include Bob only)
    followers_resp = await async_client.get(f"/api/v1/users/{alice['username']}/followers")
    assert followers_resp.status_code == 200
    followers = followers_resp.json()
    assert {f["username"] for f in followers} == {bob["username"]}

    # Check Alice following (should include Bob & Carol)
    following_resp = await async_client.get(f"/api/v1/users/{alice['username']}/following")
    assert following_resp.status_code == 200
    following = following_resp.json()
    assert {f["username"] for f in following} == {bob["username"], carol["username"]}
