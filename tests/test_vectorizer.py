"""Tests for SingleLayerVectorizer.

Whether the resulting line work is genuinely tidy enough for CAD cleanup
is a question for GeometryRegularizer, once it exists — this stage's job
is narrower: wrap each LineSegment as a Stroke, scale it correctly when a
calibration is given, and refuse to silently ignore segmentation data it
can't actually use yet.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.application.protocols import Vectorizer
from app.domain.calibration import ScaleCalibration
from app.domain.geometry import LineSegment, Point
from app.domain.layer import LayerKind
from app.domain.units import LengthUnit
from app.infrastructure.vectorization.vectorizer import SingleLayerVectorizer


@pytest.fixture
def vectorizer() -> SingleLayerVectorizer:
    return SingleLayerVectorizer()


class TestVectorizesWithoutCalibration:
    def test_one_stroke_per_segment_on_the_walls_layer(
        self, vectorizer: SingleLayerVectorizer
    ) -> None:
        segments = [
            LineSegment(Point(0, 0), Point(10, 0)),
            LineSegment(Point(0, 0), Point(0, 10)),
        ]

        result = vectorizer.vectorize(segments, segmentation=None, calibration=None)

        assert len(result) == 2
        assert all(stroke.layer == LayerKind.WALLS for stroke in result)

    def test_keeps_pixel_coordinates_unchanged_without_calibration(
        self, vectorizer: SingleLayerVectorizer
    ) -> None:
        segment = LineSegment(Point(5, 5), Point(15, 5))

        result = vectorizer.vectorize([segment], segmentation=None, calibration=None)

        (stroke,) = result
        assert stroke.geometry.points == (Point(5, 5), Point(15, 5))

    def test_empty_segmentation_dict_behaves_like_none(
        self, vectorizer: SingleLayerVectorizer
    ) -> None:
        segments = [LineSegment(Point(0, 0), Point(10, 0))]

        result = vectorizer.vectorize(segments, segmentation={}, calibration=None)

        assert len(result) == 1
        assert result[0].layer == LayerKind.WALLS


class TestVectorizesWithCalibration:
    def test_scales_coordinates_by_pixels_per_unit(
        self, vectorizer: SingleLayerVectorizer
    ) -> None:
        # 100 px/m calibration: a 100px segment becomes 1.0 unit long.
        calibration = ScaleCalibration(
            Point(0, 0), Point(0, 100), known_length=1.0, unit=LengthUnit.METRE
        )
        segment = LineSegment(Point(0, 0), Point(100, 0))

        result = vectorizer.vectorize([segment], segmentation=None, calibration=calibration)

        (stroke,) = result
        start, end = stroke.geometry.points
        assert start == Point(0, 0)
        assert end.x == pytest.approx(1.0)
        assert end.y == pytest.approx(0.0)


class TestRejectsUnsupportedSegmentation:
    def test_raises_not_implemented_for_nonempty_segmentation(
        self, vectorizer: SingleLayerVectorizer
    ) -> None:
        fake_mask = {"WINDOWS": np.zeros((10, 10), dtype=np.uint8)}
        with pytest.raises(NotImplementedError, match="Phase 3"):
            vectorizer.vectorize([], segmentation=fake_mask, calibration=None)


class TestHandlesNoSegments:
    def test_returns_empty_list_for_no_segments(
        self, vectorizer: SingleLayerVectorizer
    ) -> None:
        result = vectorizer.vectorize([], segmentation=None, calibration=None)
        assert result == []


class TestSatisfiesTheProtocol:
    def test_is_a_structural_vectorizer(self, vectorizer: SingleLayerVectorizer) -> None:
        assert isinstance(vectorizer, Vectorizer)