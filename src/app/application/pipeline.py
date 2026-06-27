"""PhotoToCadPipeline — the end-to-end use-case: one photo in, a scaled
(if calibrated) DrawingModel out, with a PNG preview and a layered DXF
written to disk.

This is the FIRST place in the codebase that calls more than one stage in
sequence — every adapter commit before this one only had to satisfy its
own Protocol in isolation. Wiring them together here is exactly what
catches cross-stage ordering mistakes a single adapter's own tests can't:
calibration is applied to Strokes AFTER regularize(), not folded into the
Vectorizer call the way looking at Vectorizer's own Protocol in isolation
might suggest — see OrthoSnapMergeRegularizer's own docstring for why
regularizing already-calibrated (real-unit-scale) Strokes silently breaks
its pixel-scale tolerances.

Stages NOT included here, on purpose, not by oversight: Preprocessor (no
adapter exists yet; EdgeDetector's own bilateral filter covers denoising
for now) and FacadeSegmenter (Phase 3, needs a real model). Both get
added to this orchestrator once they exist — there's no placeholder
parameter here pretending they already do.

Calibration is optional, and all-or-nothing: `calibration_pixel_start`,
`calibration_pixel_end`, and `calibration_known_length` must be given
together or not at all (a partial set raises ValueError rather than being
silently ignored). When given, the two pixel points must be in the
RECTIFIED image's coordinate space — the same space Strokes are in
immediately after Vectorizer/regularize — not the original, un-rectified
photo's coordinates. Getting that coordinate space right is exactly the
kind of detail only the orchestrator (the one place that actually knows
what space its own intermediate values are in) can be responsible for; a
Protocol-level test of ScaleCalibrator alone never could catch it being
wrong.
"""

from __future__ import annotations

from app.application.protocols import (
    DrawingExporter,
    EdgeDetector,
    GeometryRegularizer,
    ImageValidator,
    Rectifier,
    ScaleCalibrator,
    Vectorizer,
)
from app.domain.calibration import ScaleCalibration
from app.domain.drawing import DrawingModel
from app.domain.geometry import Point, Polyline
from app.domain.stroke import Stroke
from app.domain.units import LengthUnit

CornerQuad = tuple[Point, Point, Point, Point]


class PhotoToCadPipeline:
    def __init__(
        self,
        image_validator: ImageValidator,
        rectifier: Rectifier,
        edge_detector: EdgeDetector,
        vectorizer: Vectorizer,
        scale_calibrator: ScaleCalibrator,
        png_exporter: DrawingExporter,
        dxf_exporter: DrawingExporter,
        regularizer: GeometryRegularizer | None = None,
    ) -> None:
        self._image_validator = image_validator
        self._rectifier = rectifier
        self._edge_detector = edge_detector
        self._vectorizer = vectorizer
        self._scale_calibrator = scale_calibrator
        self._png_exporter = png_exporter
        self._dxf_exporter = dxf_exporter
        self._regularizer = regularizer

    def run(
        self,
        photo_path: str,
        manual_corners: CornerQuad,
        png_output_path: str,
        dxf_output_path: str,
        *,
        calibration_pixel_start: Point | None = None,
        calibration_pixel_end: Point | None = None,
        calibration_known_length: float | None = None,
        calibration_unit: LengthUnit = LengthUnit.MILLIMETRE,
    ) -> DrawingModel:
        image = self._image_validator.validate(photo_path)
        rectified = self._rectifier.rectify(image, manual_corners=manual_corners)
        segments = self._edge_detector.detect(rectified)

        # Pixel space, deliberately uncalibrated here even if calibration
        # input was given — see module docstring for why.
        strokes = self._vectorizer.vectorize(segments, segmentation=None, calibration=None)
        if self._regularizer is not None:
            strokes = self._regularizer.regularize(strokes)

        calibration = self._maybe_calibrate(
            calibration_pixel_start,
            calibration_pixel_end,
            calibration_known_length,
            calibration_unit,
        )
        if calibration is not None:
            strokes = [self._scale_stroke(stroke, calibration) for stroke in strokes]

        drawing = DrawingModel(
            source_image_path=photo_path,
            unit=calibration.unit if calibration is not None else LengthUnit.MILLIMETRE,
            calibration=calibration,
        )
        for stroke in strokes:
            drawing.add_stroke(stroke)

        self._png_exporter.export(drawing, png_output_path)
        self._dxf_exporter.export(drawing, dxf_output_path)
        return drawing

    def _maybe_calibrate(
        self,
        pixel_start: Point | None,
        pixel_end: Point | None,
        known_length: float | None,
        unit: LengthUnit,
    ) -> ScaleCalibration | None:
        if pixel_start is None and pixel_end is None and known_length is None:
            return None
        if pixel_start is None or pixel_end is None or known_length is None:
            raise ValueError(
                "Partial calibration input: calibration_pixel_start, "
                "calibration_pixel_end, and calibration_known_length must "
                "be given together or not at all."
            )
        return self._scale_calibrator.calibrate(pixel_start, pixel_end, known_length, unit)

    @staticmethod
    def _scale_stroke(stroke: Stroke, calibration: ScaleCalibration) -> Stroke:
        scaled_points = tuple(calibration.to_real_point(point) for point in stroke.geometry.points)
        return Stroke(
            geometry=Polyline(points=scaled_points, closed=stroke.geometry.closed),
            layer=stroke.layer,
            confidence=stroke.confidence,
        )