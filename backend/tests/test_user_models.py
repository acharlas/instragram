"""Unit tests for user profile schemas."""

from api.v1.users import UserProfilePrivate, UserProfilePublic
from models import User


def make_user(**overrides) -> User:
    defaults = {
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "sample",
        "email": "sample@example.com",
        "password_hash": "hashed",
        "name": "Sample User",
        "bio": "Bio text",
        "avatar_key": "avatars/sample.jpg",
    }
    defaults.update(overrides)
    return User(**defaults)


def test_user_profile_public_excludes_email():
    user = make_user()
    profile = UserProfilePublic.model_validate(user)
    assert profile.username == user.username
    assert profile.name == user.name
    assert not hasattr(profile, "email")


def test_user_profile_private_includes_email():
    user = make_user()
    profile = UserProfilePrivate.model_validate(user)
    assert profile.username == user.username
    assert profile.email == user.email
    assert profile.avatar_key == user.avatar_key
