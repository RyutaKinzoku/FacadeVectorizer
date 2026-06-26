"""PreviewPngExporter — renders a DrawingModel as a raster preview PNG.

Implements app.application.protocols.DrawingExporter. A quick visual
preview, not a precision deliverable — DxfExporter (this same package) is
the actual scaled CAD output. Fits the drawing's own bounding box into a
fixed-size canvas, preserving aspect ratio, rather than rendering at a
literal 1:1 pixel scale: a DrawingModel's coordinates might be raw image
pixels (uncalibrated) or real-world metres (calibrated), and either way
"fit to a nice preview size" produces a sensible image, while a literal
1:1 mapping wouldn't (a 6-metre-wide calibrated building would render as
a 6-pixel-wide PNG).

Y-axis: kept image-style, Y increasing downward, matching how the source
photo itself looks — so the preview visually resembles the rectified
photo it came from. Contrast with DxfExporter, which flips Y to match
CAD's upward-Y convention; the two exporters have different audiences
and different correct answers to the same question.

Colour order: the canvas built here is BGR, not the RGB ImageArray
contract used elsewhere in this codebase (see app.application.types) —
it never crosses a Protocol boundary as pipeline image data, it's a
private rendering buffer that goes straight into cv2.imwrite, which
itself expects BGR. Using RGB here would write a PNG with every colour
channel swapped, with no error from cv2 to catch it.
"""

from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np

from app.domain.drawing import DrawingModel
from app.domain.geometry import BoundingBox, Point

#: Target size for the longer side of the rendered preview, in pixels.
TARGET_MAX_DIMENSION = 2048

#: Fraction of the drawing's own size added as a margin on each side.
MARGIN_FRACTION = 0.05

#: BGR — see module docstring.
STROKE_COLOR_BGR = (40, 40, 40)
BACKGROUND_COLOR_BGR = (255, 255, 255)
STROKE_THICKNESS = 2


class PreviewPngExporter:
    def export(self, drawing: DrawingModel, output_path: str) -> None:
        all_points = tuple(point for stroke in drawing.strokes for point in stroke.geometry.points)
        if not all_points:
            raise ValueError("Cannot export a PNG preview with zero strokes.")

        bounds = BoundingBox.from_points(all_points)
        canvas, to_canvas = self._build_canvas(bounds)

        for stroke in drawing.strokes:
            points = [to_canvas(point) for point in stroke.geometry.points]
            for start, end in zip(points, points[1:], strict=False):
                cv2.line(canvas, start, end, STROKE_COLOR_BGR, STROKE_THICKNESS, cv2.LINE_AA)
            if stroke.geometry.closed and len(points) > 1:
                cv2.line(
                    canvas, points[-1], points[0], STROKE_COLOR_BGR, STROKE_THICKNESS, cv2.LINE_AA
                )

        if not cv2.imwrite(output_path, canvas):
            raise ValueError(
                f"Failed to write PNG to '{output_path}' — cv2.imwrite reported failure "
                "(check the path and that the parent directory exists). Unlike ezdxf's "
                "saveas, cv2.imwrite fails silently rather than raising, so this is checked "
                "explicitly."
            )

    @staticmethod
    def _build_canvas(
        bounds: BoundingBox,
    ) -> tuple[np.ndarray, Callable[[Point], tuple[int, int]]]:
        margin_x = bounds.width * MARGIN_FRACTION
        margin_y = bounds.height * MARGIN_FRACTION
        padded_width = bounds.width + 2 * margin_x
        padded_height = bounds.height + 2 * margin_y

        longer_side = max(padded_width, padded_height)
        if longer_side <= 0:
            raise ValueError("Cannot export a PNG preview: all strokes collapse to a single point.")

        scale = TARGET_MAX_DIMENSION / longer_side
        canvas_width = max(1, round(padded_width * scale))
        canvas_height = max(1, round(padded_height * scale))

        canvas = np.full((canvas_height, canvas_width, 3), BACKGROUND_COLOR_BGR, dtype=np.uint8)

        def to_canvas(point: Point) -> tuple[int, int]:
            x = round((point.x - bounds.min_x + margin_x) * scale)
            y = round((point.y - bounds.min_y + margin_y) * scale)
            return (x, y)

        return canvas, to_canvas