"""Additional coverage for auth utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Request, Response
from sqlalchemy import select

from api.v1 import auth
from models import RefreshToken, User


def _make_request_with_cookie(name: str, value: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"cookie", f"{name}={value}".encode("ascii"))],
        "query_string": b"",
        "client": ("test", 0),
        "app": None,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_register_function_success(db_session):
    payload = auth.RegisterRequest(
        username="direct_register",
        email="direct@example.com",
        password="Sup3rSecret!",
        name="Direct",
        bio="Bio",
    )
    response = await auth.register(payload, session=db_session)
    assert response.username == payload.username


@pytest.mark.asyncio
async def test_store_refresh_token_persists_record(db_session, monkeypatch):
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        auth,
        "decode_token",
        lambda token: {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        },
    )

    await auth._store_refresh_token(db_session, "user-1", "token123")
    await db_session.commit()

    result = await db_session.execute(select(RefreshToken))
    tokens = result.scalars().all()
    assert len(tokens) == 1


def test_ensure_aware_adds_timezone():
    naive = datetime(2025, 1, 1, 12, 0, 0)
    aware = auth._ensure_aware(naive)
    assert aware.tzinfo is not None


@pytest.mark.asyncio
async def test_enforce_refresh_token_limit_prunes_oldest(db_session):
    user_id = "user-limited"
    base = datetime.now(timezone.utc)
    for i in range(auth.MAX_ACTIVE_REFRESH_TOKENS + 2):
        token = RefreshToken(
            user_id=user_id,
            token_hash=f"hash-{i}",
            issued_at=base - timedelta(minutes=i),
            expires_at=base + timedelta(days=1),
        )
        db_session.add(token)
    await db_session.commit()

    await auth._enforce_refresh_token_limit(db_session, user_id)
    await db_session.commit()

    result = await db_session.execute(select(RefreshToken).where(auth._eq(RefreshToken.user_id, user_id)))
    assert len(result.scalars().all()) == auth.MAX_ACTIVE_REFRESH_TOKENS


@pytest.mark.asyncio
async def test_get_refresh_token_handles_revoked(db_session):
    token = RefreshToken(
        user_id="revoked",
        token_hash=auth._hash_refresh_token("token"),
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        revoked_at=datetime.now(timezone.utc),
    )
    db_session.add(token)
    await db_session.commit()

    with pytest.raises(auth.HTTPException) as exc:
        await auth._get_refresh_token(db_session, "token")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_refresh_token_handles_expired(db_session):
    token = RefreshToken(
        user_id="expired",
        token_hash=auth._hash_refresh_token("token"),
        issued_at=datetime.now(timezone.utc) - timedelta(days=1),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(token)
    await db_session.commit()

    with pytest.raises(auth.HTTPException):
        await auth._get_refresh_token(db_session, "token")


@pytest.mark.asyncio
async def test_get_refresh_token_missing(db_session):
    with pytest.raises(auth.HTTPException):
        await auth._get_refresh_token(db_session, "missing")


@pytest.mark.asyncio
async def test_refresh_requires_cookie(async_client):
    response = await async_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_wrong_type(async_client, monkeypatch):
    monkeypatch.setattr(auth, "decode_token", lambda token: {"type": "access", "sub": "user"})
    async_client.cookies.set("refresh_token", "token")
    response = await async_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_invalid_payload(async_client, monkeypatch):
    monkeypatch.setattr(auth, "decode_token", lambda token: {"type": "refresh", "sub": None})
    async_client.cookies.set("refresh_token", "token")
    response = await async_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_function_sets_cookies(db_session):
    user = User(
        username="login_direct",
        email="login@example.com",
        password_hash=auth.hash_password("Sup3rSecret!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    payload = auth.LoginRequest(username=user.username, password="Sup3rSecret!")
    response = Response()
    token_response = await auth.login(payload, response=response, session=db_session)

    assert token_response.access_token
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(header.startswith(f"{auth.ACCESS_COOKIE}=") for header in set_cookie_headers)


@pytest.mark.asyncio
async def test_refresh_flow_updates_token(db_session, monkeypatch):
    user = User(
        id="refresh-user",
        username="refresh_user",
        email="refresh@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()

    stored = RefreshToken(
        user_id=user.id,
        token_hash=auth._hash_refresh_token("token"),
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(stored)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    refresh_payload = {
        "sub": user.id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }

    monkeypatch.setattr(auth, "decode_token", lambda token: refresh_payload)

    request = _make_request_with_cookie(auth.REFRESH_COOKIE, "token")
    response = Response()

    result = await auth.refresh_tokens(request, response=response, session=db_session)
    assert result.access_token
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(header.startswith(f"{auth.ACCESS_COOKIE}=") for header in set_cookie_headers)
