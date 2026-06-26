"""Pillow-based ImageValidator — the pipeline's first line of defense.

Implements `app.application.protocols.ImageValidator`. Enforces the limits
from docs/architecture.md §7 (OWASP) before any other stage sees the
image: a bounded file size, a bounded pixel count (decompression-bomb
guard), and a narrow format allow-list. EXIF is used only to normalise
orientation safely — never trusted for anything else, never propagated
downstream.

Path handling: `.resolve()` and an existence check are enough here. The
source photo is a file the user picked themselves through a native file
dialog, so — unlike a web app — there is no "expected directory" to
confine it to; that confinement concern belongs to the persistence layer
(the project repository, Phase 1, which DOES read/write to app-controlled
locations).

Contract: ImageArray is always RGB, uint8, height x width x channels. Any
OpenCV-based adapter downstream (vision/) is responsible for converting to
BGR internally if it needs to — this module never leaks a Pillow- or
cv2-specific convention across the Protocol boundary.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.application.types import ImageArray

#: Hard ceiling on the source file's size on disk.
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

#: Hard ceiling on total pixel count (width * height) — the
#: decompression-bomb guard. Also installed as Pillow's own global limit
#: so a crafted file can't be decoded past this point even if our own
#: explicit check below were ever bypassed (defense in depth).
MAX_PIXELS = 64_000_000  # comfortably above any real camera photo
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

#: Narrow allow-list — common camera/export formats only.
ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "BMP", "TIFF", "WEBP"})


class PillowImageValidator:
    """Concrete ImageValidator.

    Satisfies the Protocol structurally (PEP 544) — no inheritance from
    anything in app.application required; see tests/test_protocols.py for
    why that matters.
    """

    def validate(self, path: str) -> ImageArray:
        resolved = self._resolve_existing_file(path)
        self._check_file_size(resolved)

        try:
            with Image.open(resolved) as probe:
                probe.verify()  # cheap structural check; closes the handle

            with Image.open(resolved) as image:
                self._check_format(image.format)
                # Safe orientation normalisation only — no other EXIF use,
                # nothing from EXIF is returned or stored downstream.
                oriented = ImageOps.exif_transpose(image) or image
                rgb = oriented.convert("RGB")
                self._check_pixel_count(rgb.width, rgb.height)
                return np.asarray(rgb, dtype=np.uint8)

        except UnidentifiedImageError as exc:
            raise ValueError(f"'{path}' is not a readable image.") from exc
        except Image.DecompressionBombError as exc:
            raise ValueError(f"'{path}' exceeds the decoded pixel-count limit.") from exc

    @staticmethod
    def _resolve_existing_file(path: str) -> Path:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"'{path}' does not exist or is not a file.")
        return resolved

    @staticmethod
    def _check_file_size(resolved: Path) -> None:
        size = os.path.getsize(resolved)
        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File is {size / 1024 / 1024:.1f} MB, "
                f"exceeding the {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB limit."
            )

    @staticmethod
    def _check_format(image_format: str | None) -> None:
        if image_format not in ALLOWED_FORMATS:
            raise ValueError(
                f"Unsupported image format '{image_format}'. "
                f"Allowed: {sorted(ALLOWED_FORMATS)}."
            )

    @staticmethod
    def _check_pixel_count(width: int, height: int) -> None:
        pixel_count = width * height
        if pixel_count > MAX_PIXELS:
            raise ValueError(
                f"Image is {width}x{height} ({pixel_count:,} px), "
                f"exceeding the {MAX_PIXELS:,} px limit."
            )