"""Tests for post endpoints."""

from io import BytesIO
from typing import Any, cast
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from models import Post
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
