"""MinIO client utilities."""

from __future__ import annotations

from functools import lru_cache

from minio import Minio
from minio.error import S3Error

from core import settings


@lru_cache
def get_minio_client() -> Minio:
    """Return a cached MinIO client configured from settings."""
    endpoint = settings.minio_endpoint
    access_key = settings.minio_access_key
    secret_key = settings.minio_secret_key

    # Local development runs without TLS; production can override via endpoint/port.
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )


def ensure_bucket(client: Minio | None = None) -> None:
    """Ensure the configured bucket exists."""
    client = client or get_minio_client()
    bucket_name = settings.minio_bucket

    if client.bucket_exists(bucket_name):  # pragma: no cover - network call
        return

    try:
        client.make_bucket(bucket_name)  # pragma: no cover - network call
    except S3Error as exc:  # pragma: no cover - handle race conditions
        if exc.code != "BucketAlreadyOwnedByYou":
            raise
