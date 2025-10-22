"""Refresh token store."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class RefreshToken(SQLModel, table=True):
    """Persisted refresh tokens for rotation and revocation."""

    __tablename__ = "refresh_tokens"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    token_hash: str = Field(
        sa_column=Column(String(128), unique=True, nullable=False)
    )
    issued_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    revoked_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    user: "User" = Relationship(back_populates="refresh_tokens")
