"""User domain model."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, func
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Registered application user."""

    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid4()), sa_column=Column(String(36), primary_key=True))
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
