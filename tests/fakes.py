"""Fake Protocol implementations shared across test files.

Not a test file itself (no test_ functions here) -- just the fakes for
the three stages whose own correctness is already covered by their own
dedicated test files (test_image_validator.py, test_rectifier.py,
test_edge_detector.py). Used by test_pipeline.py and test_main_window.py
so both can build a fast, deterministic pipeline without real image
files or real cv2 calls for orchestration-level tests, without
duplicating these three small classes in each file.
"""

from __future__ import annotations

import numpy as np

from app.domain.geometry import LineSegment, Point


class FakeImageValidator:
    def validate(self, path: str) -> np.ndarray:
        return np.zeros((100, 100, 3), dtype=np.uint8)


class FakeRectifier:
    def rectify(
        self,
        image: np.ndarray,
        manual_corners: tuple[Point, Point, Point, Point] | None = None,
    ) -> np.ndarray:
        return image  # pass through -- orchestration tests don't need real warps


class FakeEdgeDetector:
    """Returns a fixed, known set of segments so tests using this fake are
    exact and deterministic, instead of depending on real cv2 detection.
    """

    def __init__(self, segments: list[LineSegment]) -> None:
        self._segments = segments

    def detect(self, image: np.ndarray) -> list[LineSegment]:
        return self._segments