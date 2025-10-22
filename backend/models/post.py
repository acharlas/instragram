"""Post model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .comment import Comment
    from .like import Like
    from .user import User


class Post(SQLModel, table=True):
    """User generated photo post."""

    __tablename__ = "posts"
    __table_args__ = (Index("ix_posts_author_created_at", "author_id", "created_at"),)

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    author_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    image_key: str = Field(
        sa_column=Column(String(255), nullable=False)
    )
    caption: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
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

    author: "User" = Relationship(back_populates="posts")
    comments: list["Comment"] = Relationship(
        back_populates="post", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    likes: list["Like"] = Relationship(
        back_populates="post", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
