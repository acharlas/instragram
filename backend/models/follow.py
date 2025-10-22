"""Follow relationship model."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func
from sqlmodel import Field, SQLModel


class Follow(SQLModel, table=True):
    """Represents a follower/followee relationship."""

    __tablename__ = "follows"

    follower_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    followee_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
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
