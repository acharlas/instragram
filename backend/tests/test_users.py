"""Tests for user profile endpoints."""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4
from typing import Any, cast

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from models import User
from api.v1 import users as users_api
from services import storage


def _eq(column: Any, value: Any) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column == value)


def build_payload() -> dict[str, str | None]:
    suffix = uuid4().hex[:8]
    return {
        "username": f"user_{suffix}",
        "email": f"user_{suffix}@example.com",
        "password": "Sup3rSecret!",
        "name": "Test User",
        "bio": "Bio text",
    }


@pytest.mark.asyncio
async def test_get_user_profile(async_client: AsyncClient):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    response = await async_client.get(f"/api/v1/users/{payload['username']}")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == payload["username"]
    assert "email" not in body
    assert body["avatar_key"] is None


@pytest.mark.asyncio
async def test_update_profile_with_avatar(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    stored_objects: dict[str, bytes] = {}

    class DummyMinio:
        def bucket_exists(self, bucket_name: str) -> bool:
            return True

        def make_bucket(self, bucket_name: str) -> None:  # pragma: no cover - not used
            return None

        def put_object(self, bucket_name, object_name, data, length, content_type=None):
            stored_objects[object_name] = data.read()

    dummy_client = DummyMinio()
    monkeypatch.setattr(storage, "get_minio_client", lambda: dummy_client)
    monkeypatch.setattr(storage, "ensure_bucket", lambda client=None: None)
    monkeypatch.setattr(users_api, "get_minio_client", lambda: dummy_client)
    monkeypatch.setattr(users_api, "ensure_bucket", lambda client=None: None)

    image = Image.new("RGB", (4000, 3000), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    files = {"avatar": ("avatar.png", png_bytes, "image/png")}
    data = {"name": "Updated Name", "bio": "Updated bio"}

    response = await async_client.patch("/api/v1/me", data=data, files=files)
    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "Updated Name"
    assert result["bio"] == "Updated bio"
    assert result["avatar_key"] is not None

    assert stored_objects, "avatar should be uploaded to storage"
    stored_bytes = next(iter(stored_objects.values()))
    assert stored_bytes.startswith(b"\xff\xd8\xff")  # JPEG signature

    db_result = await db_session.execute(
        select(User).where(_eq(User.username, payload["username"]))
    )
    user = db_result.scalar_one()
    assert user.name == "Updated Name"
    assert user.bio == "Updated bio"
    assert user.avatar_key == result["avatar_key"]


@pytest.mark.asyncio
async def test_get_me_returns_private_profile(async_client: AsyncClient):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    response = await async_client.get("/api/v1/me")
    assert response.status_code == 200

    body = response.json()
    assert body["username"] == payload["username"]
    assert body["email"] == payload["email"]


@pytest.mark.asyncio
async def test_update_me_rejects_invalid_image(async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    payload = build_payload()
    await async_client.post("/api/v1/auth/register", json=payload)
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
    )

    dummy_client = object()
    monkeypatch.setattr(storage, "get_minio_client", lambda: dummy_client)
    monkeypatch.setattr(users_api, "get_minio_client", lambda: dummy_client)
    monkeypatch.setattr(storage, "ensure_bucket", lambda client=None: None)
    monkeypatch.setattr(users_api, "ensure_bucket", lambda client=None: None)

    files = {"avatar": ("avatar.jpg", b"not-an-image", "image/jpeg")}
    response = await async_client.patch("/api/v1/me", files=files)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_me_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_me_requires_auth(async_client: AsyncClient):
    response = await async_client.patch("/api/v1/me", data={"name": "Nobody"})
    assert response.status_code == 401
