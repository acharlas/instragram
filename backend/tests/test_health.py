"""Smoke tests for health endpoints."""

import pytest


@pytest.mark.asyncio
async def test_api_health_endpoint(async_client):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_app_healthz(async_client):
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
