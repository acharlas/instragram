"""Refresh token store."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlmodel import Field, SQLModel


class RefreshToken(SQLModel, table=True):
    """Persisted refresh tokens for rotation and revocation."""

    __tablename__ = "refresh_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
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
