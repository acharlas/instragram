"""Post comment model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .post import Post
    from .user import User


class Comment(SQLModel, table=True):
    """Comments authored on posts."""

    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_post_created_at", "post_id", "created_at"),)

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    post_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    author_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    text: str = Field(sa_column=Column(Text, nullable=False))
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

    post: "Post" = Relationship(back_populates="comments")
    author: "User" = Relationship(back_populates="comments")
