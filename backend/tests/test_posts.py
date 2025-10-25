"""Tests for post endpoints."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from core.config import settings
from models import Comment, Post
from api.v1 import posts as posts_api
from services import storage


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)


def make_user_payload(prefix: str) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    return {
        "username": f"{prefix}_{suffix}",
        "email": f"{prefix}_{suffix}@example.com",
        "password": "Sup3rSecret!",
    }


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (1200, 800), color=(0, 200, 100))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_create_and_get_post(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    payload = make_user_payload("author")
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    stored_objects: dict[str, bytes] = {}

    class DummyMinio:
        def bucket_exists(self, bucket_name: str) -> bool:
            return True

        def make_bucket(self, bucket_name: str) -> None:
            return None

        def put_object(self, bucket_name, object_name, data, length, content_type=None):
            stored_objects[object_name] = data.read()

    dummy_client = DummyMinio()
    monkeypatch.setattr(storage, "get_minio_client", lambda: dummy_client)
    monkeypatch.setattr(storage, "ensure_bucket", lambda client=None: None)
    monkeypatch.setattr(posts_api, "get_minio_client", lambda: dummy_client)
    monkeypatch.setattr(posts_api, "ensure_bucket", lambda client=None: None)

    image_bytes = make_image_bytes()
    files = {"image": ("photo.png", image_bytes, "image/png")}
    data = {"caption": "First shot!"}

    create_response = await async_client.post("/api/v1/posts", data=data, files=files)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["caption"] == "First shot!"
    assert created["image_key"].endswith(".jpg")

    assert stored_objects, "Image should be uploaded"

    result = await db_session.execute(select(Post))
    posts = result.scalars().all()
    assert len(posts) == 1

    post_id = created["id"]
    get_response = await async_client.get(f"/api/v1/posts/{post_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == post_id

    list_response = await async_client.get("/api/v1/posts")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


@pytest.mark.asyncio
async def test_post_requires_auth(async_client: AsyncClient):
    files = {"image": ("photo.png", make_image_bytes(), "image/png")}
    response = await async_client.post("/api/v1/posts", files=files)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_post_not_found(async_client: AsyncClient):
    payload = make_user_payload("viewer")
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    response = await async_client.get("/api/v1/posts/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_post_requires_follow_or_ownership(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    viewer_payload = make_user_payload("viewer")
    author_payload = make_user_payload("author")
    stranger_payload = make_user_payload("stranger")

    await async_client.post("/api/v1/auth/register", json=viewer_payload)
    author_response = await async_client.post("/api/v1/auth/register", json=author_payload)
    await async_client.post("/api/v1/auth/register", json=stranger_payload)

    author_id = author_response.json()["id"]

    await async_client.post(
        "/api/v1/auth/login",
        json={"username": viewer_payload["username"], "password": viewer_payload["password"]},
    )
    await async_client.post(f"/api/v1/users/{author_payload['username']}/follow")

    post = Post(author_id=author_id, image_key="posts/test.jpg", caption="Shared")
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    response = await async_client.get(f"/api/v1/posts/{post.id}")
    assert response.status_code == 200
    assert response.json()["caption"] == "Shared"

    await async_client.post(
        "/api/v1/auth/login",
        json={"username": stranger_payload["username"], "password": stranger_payload["password"]},
    )
    forbidden = await async_client.get(f"/api/v1/posts/{post.id}")
    assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_get_post_comments_requires_access(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    viewer_payload = make_user_payload("viewer")
    author_payload = make_user_payload("author")

    viewer_response = await async_client.post("/api/v1/auth/register", json=viewer_payload)
    author_response = await async_client.post("/api/v1/auth/register", json=author_payload)

    viewer_id = viewer_response.json()["id"]
    author_id = author_response.json()["id"]

    await async_client.post(
        "/api/v1/auth/login",
        json={"username": viewer_payload["username"], "password": viewer_payload["password"]},
    )
    await async_client.post(f"/api/v1/users/{author_payload['username']}/follow")

    post = Post(author_id=author_id, image_key="posts/test-comments.jpg", caption="Commented")
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    now = datetime.now(timezone.utc)
    comments = [
        Comment(
            post_id=post.id,
            author_id=viewer_id,
            text="First!",
            created_at=now,
            updated_at=now,
        ),
        Comment(
            post_id=post.id,
            author_id=author_id,
            text="Thanks!",
            created_at=now + timedelta(seconds=5),
            updated_at=now + timedelta(seconds=5),
        ),
    ]
    for comment in comments:
        db_session.add(comment)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/posts/{post.id}/comments")
    assert response.status_code == 200
    payload = response.json()
    assert [item["text"] for item in payload] == ["First!", "Thanks!"]

    await async_client.post("/api/v1/auth/logout")
    author_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": author_payload["username"], "password": author_payload["password"]},
    )
    assert author_login.status_code == 200
    author_response = await async_client.get(f"/api/v1/posts/{post.id}/comments")
    assert author_response.status_code == 200

    # Unrelated user cannot view comments
    outsider_payload = make_user_payload("outsider")
    await async_client.post("/api/v1/auth/register", json=outsider_payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": outsider_payload["username"], "password": outsider_payload["password"]},
    )
    denied = await async_client.get(f"/api/v1/posts/{post.id}/comments")
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_create_post_rejects_invalid_image(async_client: AsyncClient):
    payload = make_user_payload("invalid")
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    files = {"image": ("bad.png", b"", "image/png")}
    response = await async_client.post("/api/v1/posts", files=files)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_post_rejects_oversized_image(async_client: AsyncClient):
    payload = make_user_payload("large")
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    oversized = b"0" * (settings.upload_max_bytes + 1)
    files = {"image": ("large.png", oversized, "image/png")}
    response = await async_client.post("/api/v1/posts", files=files)
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE


@pytest.mark.asyncio
async def test_feed_returns_followee_posts(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    viewer_payload = make_user_payload("viewer")
    followee1_payload = make_user_payload("followee1")
    followee2_payload = make_user_payload("followee2")
    other_payload = make_user_payload("other")

    viewer_response = await async_client.post("/api/v1/auth/register", json=viewer_payload)
    followee1_response = await async_client.post("/api/v1/auth/register", json=followee1_payload)
    followee2_response = await async_client.post("/api/v1/auth/register", json=followee2_payload)
    await async_client.post("/api/v1/auth/register", json=other_payload)

    viewer_id = viewer_response.json()["id"]
    followee1_id = followee1_response.json()["id"]
    followee2_id = followee2_response.json()["id"]

    await async_client.post(
        "/api/v1/auth/login",
        json={"username": viewer_payload["username"], "password": viewer_payload["password"]},
    )

    await async_client.post(f"/api/v1/users/{followee1_payload['username']}/follow")
    await async_client.post(f"/api/v1/users/{followee2_payload['username']}/follow")

    now = datetime.now(timezone.utc)
    posts_to_seed = [
        Post(
            author_id=followee2_id,
            image_key="feed/followee2-latest.jpg",
            caption="Followee2 newest",
            created_at=now,
            updated_at=now,
        ),
        Post(
            author_id=followee1_id,
            image_key="feed/followee1-older.jpg",
            caption="Followee1 older",
            created_at=now - timedelta(minutes=5),
            updated_at=now - timedelta(minutes=5),
        ),
        Post(
            author_id=viewer_id,
            image_key="feed/viewer.jpg",
            caption="Viewer post",
            created_at=now - timedelta(minutes=2),
            updated_at=now - timedelta(minutes=2),
        ),
    ]
    for post in posts_to_seed:
        db_session.add(post)
    await db_session.commit()

    response = await async_client.get("/api/v1/posts/feed")
    assert response.status_code == 200
    feed = response.json()

    assert [item["caption"] for item in feed] == ["Followee2 newest", "Followee1 older"]
    assert all(item["author_id"] in {followee1_id, followee2_id} for item in feed)


@pytest.mark.asyncio
async def test_feed_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/posts/feed")
    assert response.status_code == 401
