"""Tests for DxfExporter.

Checks the things that are actually this exporter's job: real, named
layers only for kinds actually used, the Y-flip applied correctly (CAD
convention, not image convention), the right unit recorded in the DXF
header, and a real exception (not a silent failure) on bad input.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest
from ezdxf.entities import LWPolyline

from app.application.protocols import DrawingExporter
from app.domain.drawing import DrawingModel
from app.domain.geometry import Point, Polyline
from app.domain.layer import LayerKind
from app.domain.stroke import Stroke
from app.domain.units import LengthUnit
from app.infrastructure.export.dxf_exporter import DxfExporter


@pytest.fixture
def exporter() -> DxfExporter:
    return DxfExporter()


def _drawing(*strokes: Stroke, unit: LengthUnit = LengthUnit.MILLIMETRE) -> DrawingModel:
    model = DrawingModel(source_image_path="photo.jpg", unit=unit)
    for stroke in strokes:
        model.add_stroke(stroke)
    return model


class TestWritesOnlyUsedLayers:
    def test_creates_exactly_the_layers_actually_used(
        self, exporter: DxfExporter, tmp_path: Path
    ) -> None:
        drawing = _drawing(
            Stroke(geometry=Polyline(points=(Point(0, 0), Point(10, 0))), layer=LayerKind.WALLS),
            Stroke(
                geometry=Polyline(points=(Point(0, 0), Point(0, 5))), layer=LayerKind.WINDOWS
            ),
        )
        path = tmp_path / "out.dxf"
        exporter.export(drawing, str(path))

        document = ezdxf.readfile(str(path))
        layer_names = {layer.dxf.name for layer in document.layers}

        assert "WALLS" in layer_names
        assert "WINDOWS" in layer_names
        assert "DOORS" not in layer_names  # not used by any stroke -- not created
        assert "BALCONY" not in layer_names


class TestFlipsYForCadConvention:
    def test_topmost_image_point_becomes_highest_cad_y(
        self, exporter: DxfExporter, tmp_path: Path
    ) -> None:
        # Image space: top point has the SMALLER y (y increases downward).
        top_in_image = Point(0, 0)
        bottom_in_image = Point(0, 100)
        drawing = _drawing(
            Stroke(
                geometry=Polyline(points=(top_in_image, bottom_in_image)), layer=LayerKind.WALLS
            )
        )
        path = tmp_path / "out.dxf"
        exporter.export(drawing, str(path))

        document = ezdxf.readfile(str(path))
        (entity,) = list(document.modelspace())
        assert isinstance(entity, LWPolyline)
        cad_points = list(entity.get_points())
        cad_ys = [point[1] for point in cad_points]

        # In CAD space, the point that was on top in the image must end
        # up at the HIGHER y -- the flip must actually invert the order.
        assert cad_ys[0] > cad_ys[1]


class TestRecordsTheRightUnit:
    def test_metre_unit_in_the_dxf_header(self, exporter: DxfExporter, tmp_path: Path) -> None:
        drawing = _drawing(
            Stroke(geometry=Polyline(points=(Point(0, 0), Point(1, 1))), layer=LayerKind.WALLS),
            unit=LengthUnit.METRE,
        )
        path = tmp_path / "out.dxf"
        exporter.export(drawing, str(path))

        document = ezdxf.readfile(str(path))
        assert document.header["$INSUNITS"] == ezdxf.units.M


class TestRejectsBadInput:
    def test_rejects_zero_strokes(self, exporter: DxfExporter, tmp_path: Path) -> None:
        empty_drawing = DrawingModel(source_image_path="photo.jpg")
        with pytest.raises(ValueError, match="zero strokes"):
            exporter.export(empty_drawing, str(tmp_path / "out.dxf"))

    def test_raises_on_a_bad_output_path(self, exporter: DxfExporter) -> None:
        drawing = _drawing(
            Stroke(geometry=Polyline(points=(Point(0, 0), Point(1, 1))), layer=LayerKind.WALLS)
        )
        with pytest.raises(OSError):
            exporter.export(drawing, "/no/such/directory/out.dxf")


class TestSatisfiesTheProtocol:
    def test_is_a_structural_drawing_exporter(self, exporter: DxfExporter) -> None:
        assert isinstance(exporter, DrawingExporter)