"""Tests for shared FastAPI dependencies."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from api import deps
from models import User


class _DummySession:
    def __init__(self, actual):
        self.actual = actual

    async def __aenter__(self):
        return self.actual

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_db_yields_session(db_session, monkeypatch):
    async def fake_get_session():
        yield db_session

    monkeypatch.setattr(deps, "get_session", fake_get_session)

    generator = deps.get_db()
    session = await anext(generator)
    assert session is db_session
    await generator.aclose()


def _build_request_with_cookie(value: str | None) -> Request:
    headers = []
    if value is not None:
        headers.append((b"cookie", f"access_token={value}".encode("ascii")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "query_string": b"",
        "client": ("test", 1234),
        "app": None,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_current_user_accepts_int_sub(db_session, monkeypatch):
    user = User(
        id="123",
        username="int_user",
        email="int@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()

    monkeypatch.setattr(
        deps,
        "decode_token",
        lambda token: {"sub": 123, "type": "access"},
    )

    request = _build_request_with_cookie("token")
    current = await deps.get_current_user(request, db_session)
    assert current.username == "int_user"


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_type(db_session, monkeypatch):
    monkeypatch.setattr(
        deps,
        "decode_token",
        lambda token: {"sub": "abc", "type": "refresh"},
    )

    request = _build_request_with_cookie("token")
    with pytest.raises(deps.HTTPException) as exc:
        await deps.get_current_user(request, db_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_payload(db_session, monkeypatch):
    monkeypatch.setattr(
        deps,
        "decode_token",
        lambda token: {"sub": None, "type": "access"},
    )

    request = _build_request_with_cookie("token")
    with pytest.raises(deps.HTTPException):
        await deps.get_current_user(request, db_session)


@pytest.mark.asyncio
async def test_get_current_user_rejects_unknown_user(db_session, monkeypatch):
    monkeypatch.setattr(
        deps,
        "decode_token",
        lambda token: {"sub": "missing", "type": "access"},
    )

    request = _build_request_with_cookie("token")
    with pytest.raises(deps.HTTPException):
        await deps.get_current_user(request, db_session)
