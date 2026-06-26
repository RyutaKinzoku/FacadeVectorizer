"""Tests for ManualCornerRectifier.

Uses small synthetic images with deliberately-skewed quads. Whether
rectification actually un-distorts a real building facade well was
already explored in the (discarded) Phase 0 spike — what these tests
check is that the adapter behaves correctly and predictably as code:
right output size, right dtype, and it fails loudly on bad input rather
than producing a silently wrong result.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.application.protocols import Rectifier
from app.domain.geometry import Point
from app.infrastructure.vision.rectifier import ManualCornerRectifier


@pytest.fixture
def rectifier() -> ManualCornerRectifier:
    return ManualCornerRectifier()


def _blank_image(width: int = 100, height: int = 100) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


class TestRectifiesAPerfectRectangle:
    def test_axis_aligned_quad_keeps_its_own_dimensions(
        self, rectifier: ManualCornerRectifier
    ) -> None:
        image = _blank_image(100, 100)
        # A perfect 40x20 axis-aligned rectangle inside the image.
        corners = (Point(10, 10), Point(50, 10), Point(50, 30), Point(10, 30))

        result = rectifier.rectify(image, manual_corners=corners)

        assert result.shape == (20, 40, 3)  # height, width, channels
        assert result.dtype == np.uint8


class TestRectifiesASkewedQuad:
    def test_output_size_matches_the_longer_opposite_edges(
        self, rectifier: ManualCornerRectifier
    ) -> None:
        image = _blank_image(200, 200)
        # A trapezoid: wider at the bottom than the top, taller on the right.
        top_left, top_right = Point(60, 20), Point(140, 20)
        bottom_right, bottom_left = Point(180, 150), Point(20, 130)
        corners = (top_left, top_right, bottom_right, bottom_left)

        # Compute the expected size the same way the adapter does, rather
        # than hand-calculating (and risking miscalculating) the geometry.
        expected_width = round(
            max(top_left.distance_to(top_right), bottom_left.distance_to(bottom_right))
        )
        expected_height = round(
            max(top_left.distance_to(bottom_left), top_right.distance_to(bottom_right))
        )

        result = rectifier.rectify(image, manual_corners=corners)

        assert result.shape == (expected_height, expected_width, 3)


class TestRejectsBadInput:
    def test_raises_not_implemented_without_manual_corners(
        self, rectifier: ManualCornerRectifier
    ) -> None:
        with pytest.raises(NotImplementedError, match="manual_corners"):
            rectifier.rectify(_blank_image())

    def test_rejects_wrong_number_of_corners(self, rectifier: ManualCornerRectifier) -> None:
        bad_corners = (Point(0, 0), Point(10, 0), Point(10, 10))  # only 3
        with pytest.raises(ValueError, match="exactly 4"):
            rectifier.rectify(_blank_image(), manual_corners=bad_corners)  # type: ignore[arg-type]

    def test_rejects_degenerate_quad(self, rectifier: ManualCornerRectifier) -> None:
        same_point = Point(5, 5)
        corners = (same_point, same_point, same_point, same_point)
        with pytest.raises(ValueError, match="degenerate"):
            rectifier.rectify(_blank_image(), manual_corners=corners)

    def test_rejects_wrong_shaped_image(self, rectifier: ManualCornerRectifier) -> None:
        grayscale = np.zeros((50, 50), dtype=np.uint8)  # missing channel dimension
        corners = (Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10))
        with pytest.raises(ValueError, match="HxWx3"):
            rectifier.rectify(grayscale, manual_corners=corners)


class TestSatisfiesTheProtocol:
    def test_is_a_structural_rectifier(self, rectifier: ManualCornerRectifier) -> None:
        assert isinstance(rectifier, Rectifier)