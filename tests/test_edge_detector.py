"""Tests for CannyFastLineEdgeDetector.

Uses small synthetic images with unambiguous edges (a drawn rectangle) —
whether this actually produces clean, usable architectural line work on a
real photo was explored in the (discarded) Phase 0 spike. What these
tests check is that the adapter behaves correctly and predictably as
code: returns real LineSegment domain objects, handles the documented
"no lines found" case without crashing, and fails loudly on bad input.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.application.protocols import EdgeDetector
from app.domain.geometry import LineSegment
from app.infrastructure.vision.edge_detector import CannyFastLineEdgeDetector


@pytest.fixture
def detector() -> CannyFastLineEdgeDetector:
    return CannyFastLineEdgeDetector()


def _image_with_rectangle(width: int = 200, height: int = 150) -> np.ndarray:
    """An RGB image with a clearly drawn white rectangle on a black
    background -- unambiguous, high-contrast edges that any reasonable
    edge detector should find.
    """
    image = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.rectangle(image, (30, 30), (170, 120), color=(255, 255, 255), thickness=3)
    return image


def _blank_image(width: int = 100, height: int = 100) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


class TestDetectsRealEdges:
    def test_finds_line_segments_in_a_clear_rectangle(
        self, detector: CannyFastLineEdgeDetector
    ) -> None:
        result = detector.detect(_image_with_rectangle())

        assert len(result) > 0
        assert all(isinstance(segment, LineSegment) for segment in result)
        assert all(segment.length > 0 for segment in result)

    def test_segment_coordinates_stay_within_image_bounds(
        self, detector: CannyFastLineEdgeDetector
    ) -> None:
        width, height = 200, 150
        result = detector.detect(_image_with_rectangle(width, height))

        for segment in result:
            for point in (segment.start, segment.end):
                assert -1 <= point.x <= width + 1  # small tolerance for interpolation
                assert -1 <= point.y <= height + 1


class TestHandlesNoEdgesFound:
    def test_returns_an_empty_list_not_none_or_a_crash(
        self, detector: CannyFastLineEdgeDetector
    ) -> None:
        result = detector.detect(_blank_image())

        assert result == []


class TestRejectsBadInput:
    def test_rejects_wrong_shaped_image(self, detector: CannyFastLineEdgeDetector) -> None:
        grayscale = np.zeros((50, 50), dtype=np.uint8)  # missing channel dimension
        with pytest.raises(ValueError, match="HxWx3"):
            detector.detect(grayscale)


class TestSatisfiesTheProtocol:
    def test_is_a_structural_edge_detector(self, detector: CannyFastLineEdgeDetector) -> None:
        assert isinstance(detector, EdgeDetector)