"""Tests for PillowImageValidator.

Every limit gets its own small, fast test. Oversized-file and
oversized-pixel-count cases monkeypatch the module's constants down to a
tiny threshold rather than actually allocating huge images on disk —
the behaviour under test is "rejects anything over the configured limit",
not "can handle a literal 50 MB file", so there's no need to pay that
cost in the test suite.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.infrastructure.io import image_validator as iv
from app.infrastructure.io.image_validator import PillowImageValidator


@pytest.fixture
def validator() -> PillowImageValidator:
    return PillowImageValidator()


def _save(path: Path, size: tuple[int, int] = (4, 3), fmt: str = "PNG") -> Path:
    Image.new("RGB", size, color=(10, 20, 30)).save(path, format=fmt)
    return path


class TestAcceptsValidImages:
    def test_returns_rgb_uint8_array_with_correct_shape(
        self, validator: PillowImageValidator, tmp_path: Path
    ) -> None:
        path = _save(tmp_path / "photo.png", size=(4, 3))

        result = validator.validate(str(path))

        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert result.shape == (3, 4, 3)  # height, width, channels

    def test_accepts_jpeg(self, validator: PillowImageValidator, tmp_path: Path) -> None:
        path = _save(tmp_path / "photo.jpg", fmt="JPEG")
        result = validator.validate(str(path))
        assert result.shape == (3, 4, 3)


class TestRejectsInvalidPaths:
    def test_rejects_nonexistent_path(self, validator: PillowImageValidator) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            validator.validate("/no/such/file.png")

    def test_rejects_a_directory(self, validator: PillowImageValidator, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            validator.validate(str(tmp_path))

    def test_rejects_unreadable_garbage(
        self, validator: PillowImageValidator, tmp_path: Path
    ) -> None:
        path = tmp_path / "not_an_image.png"
        path.write_bytes(b"this is not an image file")
        with pytest.raises(ValueError, match="not a readable image"):
            validator.validate(str(path))


class TestEnforcesLimits:
    def test_rejects_oversized_file(
        self, validator: PillowImageValidator, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(iv, "MAX_FILE_SIZE_BYTES", 10)  # absurdly small, on purpose
        path = _save(tmp_path / "photo.png")

        with pytest.raises(ValueError, match="exceeding the"):
            validator.validate(str(path))

    def test_rejects_unsupported_format(
        self, validator: PillowImageValidator, tmp_path: Path
    ) -> None:
        path = _save(tmp_path / "photo.gif", fmt="GIF")
        with pytest.raises(ValueError, match="Unsupported image format"):
            validator.validate(str(path))

    def test_rejects_oversized_pixel_count(
        self, validator: PillowImageValidator, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(iv, "MAX_PIXELS", 8)  # 4x3 = 12 px > 8
        path = _save(tmp_path / "photo.png", size=(4, 3))

        with pytest.raises(ValueError, match="exceeding the"):
            validator.validate(str(path))


class TestSatisfiesTheProtocol:
    def test_is_a_structural_image_validator(self, validator: PillowImageValidator) -> None:
        from app.application.protocols import ImageValidator

        assert isinstance(validator, ImageValidator)