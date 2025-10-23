"""Unit tests for image processing utilities."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from services.images import JPEG_CONTENT_TYPE, MAX_IMAGE_DIMENSION, process_image_bytes


def generate_image(width: int, height: int, color: tuple[int, int, int] = (0, 128, 255)) -> bytes:
    image = Image.new("RGB", (width, height), color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_process_image_bytes_resizes_and_reencodes():
    original = generate_image(4000, 3000)
    processed, content_type = process_image_bytes(original)

    assert content_type == JPEG_CONTENT_TYPE
    # JPEG magic bytes
    assert processed.startswith(b"\xff\xd8\xff")

    result_image = Image.open(BytesIO(processed))
    width, height = result_image.size
    assert max(width, height) <= MAX_IMAGE_DIMENSION
    assert result_image.format == "JPEG"
    assert not result_image.getexif()


def test_process_image_bytes_rejects_empty():
    with pytest.raises(ValueError):
        process_image_bytes(b"")


def test_process_image_bytes_invalid_data():
    with pytest.raises(ValueError):
        process_image_bytes(b"not-an-image")


def test_process_image_bytes_rejects_excessive_dimensions():
    large = generate_image(8000, 8000)
    with pytest.raises(ValueError):
        process_image_bytes(large)
