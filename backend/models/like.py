"""Post like model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .post import Post
    from .user import User


class Like(SQLModel, table=True):
    """Tracks which users liked which posts."""

    __tablename__ = "likes"

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    post_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("posts.id", ondelete="CASCADE"),
            primary_key=True,
        )
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

    user: "User" = Relationship(back_populates="likes")
    post: "Post" = Relationship(back_populates="likes")
