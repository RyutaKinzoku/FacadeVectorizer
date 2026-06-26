"""SingleMeasurementScaleCalibrator — the only calibration strategy this
app supports for now: one user-marked pixel distance mapped to one known
real-world length (e.g. "this door is 2.10 m tall").

Implements app.application.protocols.ScaleCalibrator. All the actual
validation (known_length must be positive, the two pixel points can't be
identical) is an invariant of the ScaleCalibration value object itself —
see app.domain.calibration — so this adapter doesn't duplicate it; it
just delegates and lets the domain object raise.

Named for the strategy, not a library, since there isn't one: a future
calibration strategy (e.g. detecting a printed reference marker
automatically) would be a sibling class satisfying the same Protocol —
see docs/architecture.md §5, Strategy pattern.
"""

from __future__ import annotations

from app.domain.calibration import ScaleCalibration
from app.domain.geometry import Point
from app.domain.units import LengthUnit


class SingleMeasurementScaleCalibrator:
    def calibrate(
        self, pixel_start: Point, pixel_end: Point, known_length: float, unit: LengthUnit
    ) -> ScaleCalibration:
        return ScaleCalibration(
            pixel_start=pixel_start,
            pixel_end=pixel_end,
            known_length=known_length,
            unit=unit,
        )