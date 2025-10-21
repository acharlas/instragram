"""Pytest fixtures for the Instragram backend."""

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import create_app


@pytest.fixture(scope="session")
def app() -> Iterator[FastAPI]:
    """Create a fresh instance of the FastAPI app for the test session."""
    yield create_app()


@pytest_asyncio.fixture()
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an HTTPX async client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
