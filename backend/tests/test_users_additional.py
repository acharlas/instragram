"""Direct tests for user endpoints to improve coverage."""

from __future__ import annotations

import pytest

from api.v1 import users
from models import Follow, User


def _make_user(username: str, **extra) -> User:
    defaults = {
        "id": f"id-{username}",
        "username": username,
        "email": f"{username}@example.com",
        "password_hash": "hash",
    }
    defaults.update(extra)
    return User(**defaults)


@pytest.mark.asyncio
async def test_search_users_direct(db_session):
    current = _make_user("current")
    alice = _make_user("alice", name="Alice Doe")
    db_session.add_all([current, alice])
    await db_session.commit()

    results = await users.search_users(q="ali", limit=10, current_user=current, session=db_session)
    assert [item.username for item in results] == ["alice"]


@pytest.mark.asyncio
async def test_get_user_profile_not_found(db_session):
    with pytest.raises(users.HTTPException):
        await users.get_user_profile("missing", session=db_session)


@pytest.mark.asyncio
async def test_update_me_commits_changes(db_session):
    current = _make_user("me", name="Old")
    db_session.add(current)
    await db_session.commit()

    result = await users.update_me(
        name="New Name",
        bio="New bio",
        avatar=None,
        current_user=current,
        session=db_session,
    )
    assert result.name == "New Name"


@pytest.mark.asyncio
async def test_follow_and_unfollow_direct(db_session):
    follower = _make_user("follower")
    followee = _make_user("followee")
    db_session.add_all([follower, followee])
    await db_session.commit()

    follow_result = await users.follow_user(
        followee.username,
        current_user=follower,
        session=db_session,
    )
    assert follow_result["detail"] == "Followed"

    unfollow_result = await users.unfollow_user(
        followee.username,
        current_user=follower,
        session=db_session,
    )
    assert unfollow_result["detail"] == "Unfollowed"


@pytest.mark.asyncio
async def test_list_followers_and_following(db_session):
    alice = _make_user("alice")
    bob = _make_user("bob")
    charlie = _make_user("charlie")
    db_session.add_all([alice, bob, charlie])
    await db_session.commit()

    db_session.add(Follow(follower_id=bob.id, followee_id=alice.id))
    db_session.add(Follow(follower_id=alice.id, followee_id=charlie.id))
    await db_session.commit()

    followers = await users.list_followers(alice.username, session=db_session)
    assert [item.username for item in followers] == ["bob"]

    following = await users.list_following(alice.username, session=db_session)
    assert [item.username for item in following] == ["charlie"]
