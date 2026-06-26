"""Unit tests for the domain layer: geometry, calibration, layers, strokes,
and the DrawingModel aggregate. Pure logic, no Qt, no filesystem, no I/O —
these should stay fast forever.
"""

from __future__ import annotations

import pytest

from app.domain import (
    BoundingBox,
    DrawingModel,
    Layer,
    LayerKind,
    LengthUnit,
    LineSegment,
    Point,
    Polyline,
    ScaleCalibration,
    Stroke,
)


class TestGeometry:
    def test_point_distance(self) -> None:
        assert Point(0, 0).distance_to(Point(3, 4)) == 5.0

    def test_line_segment_length(self) -> None:
        segment = LineSegment(Point(0, 0), Point(0, 10))
        assert segment.length == 10.0

    def test_polyline_requires_at_least_two_points(self) -> None:
        with pytest.raises(ValueError, match="at least two points"):
            Polyline(points=(Point(0, 0),))

    def test_polyline_accepts_two_points(self) -> None:
        polyline = Polyline(points=(Point(0, 0), Point(1, 1)))
        assert len(polyline.points) == 2
        assert polyline.closed is False

    def test_bounding_box_from_points(self) -> None:
        box = BoundingBox.from_points((Point(0, 0), Point(4, 2), Point(-1, 5)))
        assert (box.min_x, box.min_y, box.max_x, box.max_y) == (-1, 0, 4, 5)
        assert box.width == 5
        assert box.height == 5

    def test_bounding_box_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="zero points"):
            BoundingBox.from_points(())


class TestScaleCalibration:
    def test_pixels_per_unit(self) -> None:
        # A 200px line representing a 2.0 m door -> 100 px/m.
        calibration = ScaleCalibration(
            pixel_start=Point(0, 0),
            pixel_end=Point(0, 200),
            known_length=2.0,
            unit=LengthUnit.METRE,
        )
        assert calibration.pixels_per_unit == pytest.approx(100.0)

    def test_to_real_length(self) -> None:
        calibration = ScaleCalibration(
            pixel_start=Point(0, 0),
            pixel_end=Point(0, 200),
            known_length=2.0,
            unit=LengthUnit.METRE,
        )
        # 100 px at 100 px/m -> 1.0 m.
        assert calibration.to_real_length(100.0) == pytest.approx(1.0)

    def test_rejects_non_positive_known_length(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            ScaleCalibration(Point(0, 0), Point(0, 200), known_length=0, unit=LengthUnit.METRE)

    def test_rejects_identical_pixel_points(self) -> None:
        with pytest.raises(ValueError, match="same point"):
            ScaleCalibration(Point(5, 5), Point(5, 5), known_length=1.0, unit=LengthUnit.METRE)


class TestLayer:
    def test_layer_name_matches_kind_value(self) -> None:
        assert Layer(kind=LayerKind.WINDOWS).name == "WINDOWS"

    def test_layer_defaults(self) -> None:
        layer = Layer(kind=LayerKind.WALLS)
        assert layer.color == 7
        assert layer.visible is True
        assert layer.locked is False


class TestStroke:
    def test_confidence_defaults_to_one(self) -> None:
        polyline = Polyline(points=(Point(0, 0), Point(1, 1)))
        stroke = Stroke(geometry=polyline, layer=LayerKind.WALLS)
        assert stroke.confidence == 1.0

    @pytest.mark.parametrize("confidence", [-0.1, 1.1])
    def test_rejects_out_of_range_confidence(self, confidence: float) -> None:
        polyline = Polyline(points=(Point(0, 0), Point(1, 1)))
        with pytest.raises(ValueError, match="confidence"):
            Stroke(geometry=polyline, layer=LayerKind.WALLS, confidence=confidence)


class TestDrawingModel:
    def test_starts_uncalibrated_with_default_layers(self) -> None:
        model = DrawingModel(source_image_path="photo.jpg")
        assert model.is_calibrated is False
        assert {layer.kind for layer in model.layers} == set(LayerKind)
        assert model.strokes == []

    def test_add_stroke_and_filter_by_layer(self) -> None:
        model = DrawingModel(source_image_path="photo.jpg")
        wall_stroke = Stroke(
            geometry=Polyline(points=(Point(0, 0), Point(1, 0))), layer=LayerKind.WALLS
        )
        window_stroke = Stroke(
            geometry=Polyline(points=(Point(0, 0), Point(0, 1))), layer=LayerKind.WINDOWS
        )

        model.add_stroke(wall_stroke)
        model.add_stroke(window_stroke)

        assert model.strokes_on(LayerKind.WALLS) == [wall_stroke]
        assert model.strokes_on(LayerKind.WINDOWS) == [window_stroke]
        assert model.strokes_on(LayerKind.DOORS) == []

    def test_becomes_calibrated_once_calibration_is_set(self) -> None:
        model = DrawingModel(source_image_path="photo.jpg")
        model.calibration = ScaleCalibration(
            Point(0, 0), Point(0, 200), known_length=2.0, unit=LengthUnit.METRE
        )
        assert model.is_calibrated is True