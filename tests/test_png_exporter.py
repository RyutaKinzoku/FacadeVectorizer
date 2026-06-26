"""Tests for PreviewPngExporter.

Checks the things that are actually this exporter's job: it fits the
drawing to a sensible preview size regardless of coordinate scale, it
produces a real, openable PNG, and it fails loudly (not silently, the way
cv2.imwrite itself does) on bad input or a bad path.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from app.application.protocols import DrawingExporter
from app.domain.drawing import DrawingModel
from app.domain.geometry import Point, Polyline
from app.domain.layer import LayerKind
from app.domain.stroke import Stroke
from app.infrastructure.export.png_exporter import PreviewPngExporter


@pytest.fixture
def exporter() -> PreviewPngExporter:
    return PreviewPngExporter()


def _drawing_with_one_stroke(p1: Point, p2: Point) -> DrawingModel:
    model = DrawingModel(source_image_path="photo.jpg")
    model.add_stroke(Stroke(geometry=Polyline(points=(p1, p2)), layer=LayerKind.WALLS))
    return model


class TestExportsAnOpenablePng:
    def test_writes_a_file_with_the_expected_max_dimension(
        self, exporter: PreviewPngExporter, tmp_path: Path
    ) -> None:
        drawing = _drawing_with_one_stroke(Point(0, 0), Point(100, 50))
        output_path = tmp_path / "preview.png"

        exporter.export(drawing, str(output_path))

        assert output_path.exists()
        image = cv2.imread(str(output_path))
        assert image is not None
        assert max(image.shape[:2]) == 2048  # TARGET_MAX_DIMENSION

    def test_scale_independent_of_coordinate_magnitude(
        self, exporter: PreviewPngExporter, tmp_path: Path
    ) -> None:
        # A drawing in real-world metres (small numbers) should fit the
        # canvas exactly as well as one in raw pixel space (large numbers)
        # -- that's the whole point of fitting to the bounding box.
        small_scale = _drawing_with_one_stroke(Point(0, 0), Point(6.0, 3.0))
        large_scale = _drawing_with_one_stroke(Point(0, 0), Point(1800, 900))

        small_path = tmp_path / "small.png"
        large_path = tmp_path / "large.png"
        exporter.export(small_scale, str(small_path))
        exporter.export(large_scale, str(large_path))

        small_image = cv2.imread(str(small_path))
        large_image = cv2.imread(str(large_path))
        assert small_image.shape == large_image.shape


class TestRejectsBadInput:
    def test_rejects_zero_strokes(self, exporter: PreviewPngExporter, tmp_path: Path) -> None:
        empty_drawing = DrawingModel(source_image_path="photo.jpg")
        with pytest.raises(ValueError, match="zero strokes"):
            exporter.export(empty_drawing, str(tmp_path / "out.png"))

    def test_rejects_all_points_collapsing_to_one(
        self, exporter: PreviewPngExporter, tmp_path: Path
    ) -> None:
        same_point = Point(5, 5)
        drawing = _drawing_with_one_stroke(same_point, same_point)
        with pytest.raises(ValueError, match="single point"):
            exporter.export(drawing, str(tmp_path / "out.png"))

    def test_raises_on_a_bad_output_path(self, exporter: PreviewPngExporter) -> None:
        drawing = _drawing_with_one_stroke(Point(0, 0), Point(10, 10))
        with pytest.raises(ValueError, match="Failed to write PNG"):
            exporter.export(drawing, "/no/such/directory/out.png")


class TestSatisfiesTheProtocol:
    def test_is_a_structural_drawing_exporter(self, exporter: PreviewPngExporter) -> None:
        assert isinstance(exporter, DrawingExporter)