"""Contract tests for the pipeline stage Protocols.

These don't test pipeline behaviour (there isn't any yet) — they prove the
Protocols themselves are well-formed: a plain class that implements every
method, with no inheritance from anything in app.application, structurally
satisfies all nine. If a future edit renames a Protocol method without
updating this fake, this test catches the drift immediately.
"""

from __future__ import annotations

import numpy as np

from app.application.protocols import (
    DrawingExporter,
    EdgeDetector,
    FacadeSegmenter,
    GeometryRegularizer,
    ImageValidator,
    Preprocessor,
    Rectifier,
    ScaleCalibrator,
    Vectorizer,
)
from app.application.types import ImageArray
from app.domain.calibration import ScaleCalibration
from app.domain.drawing import DrawingModel
from app.domain.geometry import LineSegment, Point, Polyline
from app.domain.layer import LayerKind
from app.domain.stroke import Stroke
from app.domain.units import LengthUnit


class FakeStageImplementation:
    """One class, no inheritance, implementing every stage method.

    Structural typing (PEP 544) means this satisfies all nine Protocols
    below purely by having the matching methods — exactly what lets a
    classic-CV adapter and a learned-ONNX adapter both be valid
    EdgeDetectors without sharing a base class.
    """

    def validate(self, path: str) -> ImageArray:
        return np.zeros((1, 1, 3), dtype=np.uint8)

    def process(self, image: ImageArray) -> ImageArray:
        return image

    def rectify(
        self,
        image: ImageArray,
        manual_corners: tuple[Point, Point, Point, Point] | None = None,
    ) -> ImageArray:
        return image

    def calibrate(
        self, pixel_start: Point, pixel_end: Point, known_length: float
    ) -> ScaleCalibration:
        return ScaleCalibration(pixel_start, pixel_end, known_length, LengthUnit.METRE)

    def detect(self, image: ImageArray) -> list[LineSegment]:
        return []

    def segment(self, image: ImageArray) -> dict[str, ImageArray]:
        return {}

    def vectorize(
        self,
        segments: list[LineSegment],
        segmentation: dict[str, ImageArray] | None,
        calibration: ScaleCalibration | None,
    ) -> list[Stroke]:
        return []

    def regularize(self, strokes: list[Stroke]) -> list[Stroke]:
        return strokes

    def export(self, drawing: DrawingModel, output_path: str) -> None:
        return None


def test_fake_satisfies_every_stage_protocol() -> None:
    fake = FakeStageImplementation()

    assert isinstance(fake, ImageValidator)
    assert isinstance(fake, Preprocessor)
    assert isinstance(fake, Rectifier)
    assert isinstance(fake, ScaleCalibrator)
    assert isinstance(fake, EdgeDetector)
    assert isinstance(fake, FacadeSegmenter)
    assert isinstance(fake, Vectorizer)
    assert isinstance(fake, GeometryRegularizer)
    assert isinstance(fake, DrawingExporter)


def test_fake_calibrate_round_trips_through_the_real_value_object() -> None:
    fake = FakeStageImplementation()
    calibration = fake.calibrate(Point(0, 0), Point(0, 200), known_length=2.0)
    assert calibration.pixels_per_unit > 0


def test_fake_export_accepts_a_real_drawing_model() -> None:
    fake = FakeStageImplementation()
    model = DrawingModel(source_image_path="photo.jpg")
    model.add_stroke(
        Stroke(geometry=Polyline(points=(Point(0, 0), Point(1, 1))), layer=LayerKind.WALLS)
    )
    # Should not raise — the Protocol's shape is what's under test here.
    fake.export(model, "ignored.dxf")