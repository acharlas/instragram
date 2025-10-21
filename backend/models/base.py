"""Declarative base for ORM models."""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(AsyncAttrs, MappedAsDataclass, DeclarativeBase):
    """Base class for models with async support."""

    pass
