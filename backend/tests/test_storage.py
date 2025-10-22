"""Tests for MinIO storage helpers."""

from unittest.mock import MagicMock

import pytest

from services import storage


@pytest.fixture(autouse=True)
def _reset_cache():
    storage.get_minio_client.cache_clear()
    yield
    storage.get_minio_client.cache_clear()


def test_get_minio_client_uses_settings(monkeypatch):
    mock_client = MagicMock(name="Minio")
    created_clients = []

    def fake_minio(endpoint, access_key, secret_key, secure):
        created_clients.append(
            {
                "endpoint": endpoint,
                "access_key": access_key,
                "secret_key": secret_key,
                "secure": secure,
            }
        )
        return mock_client

    monkeypatch.setattr(storage, "Minio", fake_minio)

    client = storage.get_minio_client()
    assert client is mock_client
    assert storage.get_minio_client() is client  # cached

    assert created_clients == [
        {
            "endpoint": storage.settings.minio_endpoint,
            "access_key": storage.settings.minio_access_key,
            "secret_key": storage.settings.minio_secret_key,
            "secure": False,
        }
    ]


def test_ensure_bucket_existing(monkeypatch):
    client = MagicMock()
    client.bucket_exists.return_value = True

    storage.ensure_bucket(client)
    client.bucket_exists.assert_called_once_with(storage.settings.minio_bucket)
    client.make_bucket.assert_not_called()


def test_ensure_bucket_creates_when_missing(monkeypatch):
    client = MagicMock()
    client.bucket_exists.return_value = False

    storage.ensure_bucket(client)

    client.bucket_exists.assert_called_once_with(storage.settings.minio_bucket)
    client.make_bucket.assert_called_once_with(storage.settings.minio_bucket)
