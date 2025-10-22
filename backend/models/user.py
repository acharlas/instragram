"""User domain model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, String, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .comment import Comment
    from .like import Like
    from .post import Post
    from .refresh_token import RefreshToken


class User(SQLModel, table=True):
    """Registered application user."""

    __tablename__ = "users"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    username: str = Field(
        sa_column=Column(String(30), unique=True, nullable=False, index=True)
    )
    email: str = Field(
        sa_column=Column(String(255), unique=True, nullable=False, index=True)
    )
    password_hash: str = Field(
        sa_column=Column(String(255), nullable=False)
    )
    name: str | None = Field(
        default=None, sa_column=Column(String(80), nullable=True)
    )
    bio: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    avatar_key: str | None = Field(
        default=None, sa_column=Column(String(255), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
    )

    posts: list["Post"] = Relationship(
        back_populates="author", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    comments: list["Comment"] = Relationship(
        back_populates="author", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    likes: list["Like"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
