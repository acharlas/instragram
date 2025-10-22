"""Image processing utilities for uploads."""

from __future__ import annotations

from io import BytesIO
from typing import Tuple, cast

from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.Image import Image as PILImage

try:  # Pillow >= 9.1
    from PIL.Image import Resampling

    RESAMPLE_FILTER = Resampling.LANCZOS
except ImportError:  # pragma: no cover - fallback for older versions
    RESAMPLE_FILTER = Image.LANCZOS  # type: ignore[attr-defined]

MAX_IMAGE_DIMENSION = 2048
JPEG_CONTENT_TYPE = "image/jpeg"


def process_image_bytes(data: bytes) -> Tuple[bytes, str]:
    """Resize, re-encode, and strip EXIF data from an uploaded image."""
    if not data:
        raise ValueError("Image file is empty")

    try:
        image = cast(PILImage, Image.open(BytesIO(data)))
    except UnidentifiedImageError as exc:  # pragma: no cover - defensive
        raise ValueError("Unsupported image file") from exc

    image = ImageOps.exif_transpose(image)
    width, height = image.size
    scale = min(MAX_IMAGE_DIMENSION / width, MAX_IMAGE_DIMENSION / height, 1.0)
    if scale < 1.0:
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = cast(PILImage, image.resize(new_size, RESAMPLE_FILTER))

    image = image.convert("RGB")

    output = BytesIO()
    image.save(output, format="JPEG", quality=85, optimize=True)
    return output.getvalue(), JPEG_CONTENT_TYPE
