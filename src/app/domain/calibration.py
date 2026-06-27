"""Scale calibration: the single real-world measurement that turns a
pixel-space drawing into a correctly scaled one.

A single photograph carries no absolute scale (see docs/architecture.md,
"Honest feasibility framing", point 1). The user supplies one known
real-world dimension — e.g. "this door is 2.10 m tall" — by marking two
points in the rectified image. Everything downstream is scaled from this
one input; there is no other source of scale in this application.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.geometry import Point
from app.domain.units import LengthUnit


@dataclass(frozen=True, slots=True)
class ScaleCalibration:
    """Maps pixel distances in the rectified image to real-world length."""

    pixel_start: Point
    pixel_end: Point
    known_length: float
    unit: LengthUnit

    def __post_init__(self) -> None:
        if self.known_length <= 0:
            raise ValueError("known_length must be a positive number.")
        if self.pixel_start.distance_to(self.pixel_end) == 0:
            raise ValueError("pixel_start and pixel_end cannot be the same point.")

    @property
    def pixels_per_unit(self) -> float:
        """Pixel distance corresponding to one `unit` of real length."""
        pixel_distance = self.pixel_start.distance_to(self.pixel_end)
        return pixel_distance / self.known_length

    def to_real_length(self, pixel_distance: float) -> float:
        """Convert a pixel distance to real-world length, in `self.unit`."""
        return pixel_distance / self.pixels_per_unit

    def to_real_point(self, pixel_point: Point) -> Point:
        """Convert a pixel-space point to a real-world-unit point.

        Scales both axes by the same pixels_per_unit, assuming the
        isotropic scale a properly rectified, fronto-parallel image
        should have — even though the calibration measurement itself was
        only taken along one axis. Same assumption Vectorizer already
        documented; this method exists so that assumption lives in one
        place instead of being re-implemented at each call site (the
        orchestrator needs this exact operation too, applied to already-
        regularized Strokes, not just at Vectorizer's own call site).
        """
        scale = self.pixels_per_unit
        return Point(x=pixel_point.x / scale, y=pixel_point.y / scale)