"""Tests for PhotoToCadPipeline.

ImageValidator, Rectifier, and EdgeDetector are faked (see tests/fakes.py
for why and for what each fake does) so these tests control exactly what
flows into the rest of the pipeline with an exact, deterministic input.
Vectorizer, GeometryRegularizer, ScaleCalibrator, and both exporters are
the REAL implementations: the point of testing an orchestrator is
verifying the real pieces actually chain together correctly -- including
the ordering constraint documented in both PhotoToCadPipeline's and
OrthoSnapMergeRegularizer's docstrings -- not re-mocking everything into
isolation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.application.pipeline import PhotoToCadPipeline
from app.domain.geometry import LineSegment, Point
from app.domain.units import LengthUnit
from app.infrastructure.calibration.scale_calibrator import SingleMeasurementScaleCalibrator
from app.infrastructure.export.dxf_exporter import DxfExporter
from app.infrastructure.export.png_exporter import PreviewPngExporter
from app.infrastructure.regularization.regularizer import OrthoSnapMergeRegularizer
from app.infrastructure.vectorization.vectorizer import SingleLayerVectorizer
from tests.fakes import FakeEdgeDetector, FakeImageValidator, FakeRectifier

SOME_CORNERS = (Point(0, 0), Point(99, 0), Point(99, 99), Point(0, 99))


def _build_pipeline(
    segments: list[LineSegment], with_regularizer: bool = True
) -> PhotoToCadPipeline:
    return PhotoToCadPipeline(
        image_validator=FakeImageValidator(),
        rectifier=FakeRectifier(),
        edge_detector=FakeEdgeDetector(segments),
        vectorizer=SingleLayerVectorizer(),
        scale_calibrator=SingleMeasurementScaleCalibrator(),
        png_exporter=PreviewPngExporter(),
        dxf_exporter=DxfExporter(),
        regularizer=OrthoSnapMergeRegularizer() if with_regularizer else None,
    )


class TestRunsEndToEndWithoutCalibration:
    def test_produces_a_drawing_and_writes_both_files(self, tmp_path: Path) -> None:
        segments = [LineSegment(Point(10, 10), Point(90, 10))]
        pipeline = _build_pipeline(segments)
        png_path = tmp_path / "out.png"
        dxf_path = tmp_path / "out.dxf"

        drawing = pipeline.run("ignored.jpg", SOME_CORNERS, str(png_path), str(dxf_path))

        assert png_path.exists()
        assert dxf_path.exists()
        assert drawing.is_calibrated is False
        assert len(drawing.strokes) >= 1


class TestRunsEndToEndWithCalibration:
    def test_strokes_end_up_scaled_to_real_units(self, tmp_path: Path) -> None:
        # A 100px segment; calibrate 100px == 1.0 metre -- the resulting
        # stroke should end up about 1.0 unit long, not 100.
        segments = [LineSegment(Point(0, 0), Point(100, 0))]
        pipeline = _build_pipeline(segments)

        drawing = pipeline.run(
            "ignored.jpg",
            SOME_CORNERS,
            str(tmp_path / "out.png"),
            str(tmp_path / "out.dxf"),
            calibration_pixel_start=Point(0, 0),
            calibration_pixel_end=Point(100, 0),
            calibration_known_length=1.0,
            calibration_unit=LengthUnit.METRE,
        )

        assert drawing.is_calibrated is True
        assert drawing.unit == LengthUnit.METRE
        (stroke,) = drawing.strokes
        start, end = stroke.geometry.points
        assert start.distance_to(end) == pytest.approx(1.0, abs=0.05)


class TestRejectsPartialCalibrationInput:
    def test_raises_when_only_some_calibration_args_are_given(self, tmp_path: Path) -> None:
        pipeline = _build_pipeline([LineSegment(Point(0, 0), Point(10, 0))])

        with pytest.raises(ValueError, match="together or not at all"):
            pipeline.run(
                "ignored.jpg",
                SOME_CORNERS,
                str(tmp_path / "out.png"),
                str(tmp_path / "out.dxf"),
                calibration_pixel_start=Point(0, 0),
                # pixel_end and known_length both omitted on purpose
            )


class TestRegularizerIsOptional:
    def test_skips_regularization_when_none(self, tmp_path: Path) -> None:
        # Two overlapping fragments that WOULD merge if regularized.
        segments = [
            LineSegment(Point(0, 50), Point(40, 50)),
            LineSegment(Point(35, 50), Point(90, 50)),
        ]
        with_regularizer = _build_pipeline(segments, with_regularizer=True)
        without_regularizer = _build_pipeline(segments, with_regularizer=False)

        drawing_with = with_regularizer.run(
            "ignored.jpg", SOME_CORNERS, str(tmp_path / "a.png"), str(tmp_path / "a.dxf")
        )
        drawing_without = without_regularizer.run(
            "ignored.jpg", SOME_CORNERS, str(tmp_path / "b.png"), str(tmp_path / "b.dxf")
        )

        assert len(drawing_with.strokes) < len(drawing_without.strokes)