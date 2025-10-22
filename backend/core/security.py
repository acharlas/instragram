"""Security utilities: password hashing and JWT helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHash, VerifyMismatchError
from jose import JWTError, jwt

from .config import settings

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Return an Argon2id hash for the supplied password."""
    if not password:
        raise ValueError("password must be provided")
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Check whether a password matches a stored Argon2id hash."""
    try:
        return _password_hasher.verify(hashed_password, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Determine whether the stored hash should be upgraded."""
    try:
        return _password_hasher.check_needs_rehash(hashed_password)
    except InvalidHash:
        return True


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid4().hex,
    }
    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(subject: str, expires: timedelta | None = None) -> str:
    """Issue a signed JWT access token for the authenticated subject."""
    ttl = expires or timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(subject, ttl, token_type="access")


def create_refresh_token(subject: str, expires: timedelta | None = None) -> str:
    """Issue a signed JWT refresh token with a longer lifetime."""
    ttl = expires or timedelta(minutes=settings.refresh_token_expire_minutes)
    return _create_token(subject, ttl, token_type="refresh")


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT, returning its claims payload."""
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:  # pragma: no cover - passthrough for caller handling
        raise ValueError("Invalid token") from exc
