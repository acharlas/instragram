"""Tests for security helpers."""

from datetime import timedelta

import pytest

from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("super-secret-password")
    assert hashed != "super-secret-password"
    assert verify_password("super-secret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_needs_rehash_for_valid_hash():
    hashed = hash_password("another-secret")
    assert needs_rehash(hashed) is False


def test_access_token_contains_expected_claims():
    token = create_access_token("user-id", expires=timedelta(minutes=5))
    payload = decode_token(token)

    assert payload["sub"] == "user-id"
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]


def test_refresh_token_has_refresh_type():
    token = create_refresh_token("user-id", expires=timedelta(minutes=10))
    payload = decode_token(token)

    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-id"
