"""Minimal database seed script for local development.

Usage:
    uv run python scripts/seed.py
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from core.security import hash_password  # noqa: E402
from db.session import AsyncSessionMaker  # noqa: E402
from models import Follow, Post, User  # noqa: E402


SEED_USERS = [
    {
        "username": "demo_alex",
        "email": "alex@example.com",
        "name": "Alex Demo",
        "bio": "Trying out Instragram!",
    },
    {
        "username": "demo_bella",
        "email": "bella@example.com",
        "name": "Bella Demo",
        "bio": "Coffee lover ☕",
    },
    {
        "username": "demo_cara",
        "email": "cara@example.com",
        "name": "Cara Demo",
        "bio": "Photographer in training.",
    },
]

SEED_POSTS = [
    {
        "username": "demo_alex",
        "image_key": "demo/alex-1.jpg",
        "caption": "Sunny day snapshots.",
    },
    {
        "username": "demo_bella",
        "image_key": "demo/bella-coffee.jpg",
        "caption": "First latte art attempt!",
    },
]

SEED_FOLLOWS: Sequence[tuple[str, str]] = [
    ("demo_alex", "demo_bella"),
    ("demo_bella", "demo_cara"),
    ("demo_cara", "demo_alex"),
]

DEFAULT_PASSWORD = "password123"


async def get_or_create_user(session, payload: dict) -> User:
    result = await session.execute(select(User).where(User.username == payload["username"]))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        username=payload["username"],
        email=payload["email"],
        name=payload.get("name"),
        bio=payload.get("bio"),
        password_hash=hash_password(DEFAULT_PASSWORD),
    )
    session.add(user)
    await session.flush()
    return user


async def ensure_posts(session, users: dict[str, User]) -> None:
    for post_payload in SEED_POSTS:
        author = users[post_payload["username"]]
        result = await session.execute(
            select(Post).where(
                Post.author_id == author.id,
                Post.image_key == post_payload["image_key"],
            )
        )
        if result.scalar_one_or_none():
            continue

        session.add(
            Post(
                author_id=author.id,
                image_key=post_payload["image_key"],
                caption=post_payload.get("caption"),
            )
        )


async def ensure_follows(session, users: dict[str, User]) -> None:
    for follower_username, followee_username in SEED_FOLLOWS:
        follower = users[follower_username]
        followee = users[followee_username]

        result = await session.execute(
            select(Follow).where(
                Follow.follower_id == follower.id,
                Follow.followee_id == followee.id,
            )
        )
        if result.scalar_one_or_none():
            continue

        session.add(Follow(follower_id=follower.id, followee_id=followee.id))


async def seed() -> None:
    async with AsyncSessionMaker() as session:
        users: dict[str, User] = {}
        for payload in SEED_USERS:
            user = await get_or_create_user(session, payload)
            users[user.username] = user

        await ensure_posts(session, users)
        await ensure_follows(session, users)

        await session.commit()

    print("✅ Seed data inserted. Default password:", DEFAULT_PASSWORD)


if __name__ == "__main__":
    asyncio.run(seed())
