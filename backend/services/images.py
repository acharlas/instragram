"""Image processing utilities for uploads."""

from __future__ import annotations

from io import BytesIO
from typing import Tuple, cast

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.Image import Image as PILImage

try:  # Pillow >= 9.1
    from PIL.Image import Resampling

    RESAMPLE_FILTER = Resampling.LANCZOS
except ImportError:  # pragma: no cover - fallback for older versions
    RESAMPLE_FILTER = Image.LANCZOS  # type: ignore[attr-defined]

MAX_IMAGE_DIMENSION = 2048
MAX_IMAGE_PIXELS = MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION * 12
JPEG_CONTENT_TYPE = "image/jpeg"
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class UploadTooLargeError(ValueError):
    """Raised when an uploaded image exceeds the configured size limit."""


def _ensure_safe_pixel_count(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("Image has invalid dimensions")
    if width * height > MAX_IMAGE_PIXELS:
        raise ValueError("Image dimensions exceed safety limits")


async def read_upload_file(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an UploadFile into memory with a strict size bound."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    await upload.seek(0)
    chunk_size = max(1, min(UPLOAD_CHUNK_SIZE, max_bytes))
    total = 0
    chunks: list[bytes] = []

    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise UploadTooLargeError("Uploaded image exceeds the maximum allowed size")
        chunks.append(chunk)

    return b"".join(chunks)


def process_image_bytes(data: bytes) -> Tuple[bytes, str]:
    """Resize, re-encode, and strip EXIF data from an uploaded image."""
    if not data:
        raise ValueError("Image file is empty")

    try:
        image = cast(PILImage, Image.open(BytesIO(data)))
    except UnidentifiedImageError as exc:  # pragma: no cover - defensive
        raise ValueError("Unsupported image file") from exc

    width, height = image.size
    _ensure_safe_pixel_count(width, height)

    image = ImageOps.exif_transpose(image)
    width, height = image.size
    _ensure_safe_pixel_count(width, height)

    scale = min(MAX_IMAGE_DIMENSION / width, MAX_IMAGE_DIMENSION / height, 1.0)
    if scale < 1.0:
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = cast(PILImage, image.resize(new_size, RESAMPLE_FILTER))

    image = image.convert("RGB")

    output = BytesIO()
    image.save(output, format="JPEG", quality=85, optimize=True)
    return output.getvalue(), JPEG_CONTENT_TYPE
