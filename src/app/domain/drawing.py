"""DrawingModel — the aggregate root: everything needed to render and
export one project's elevation drawing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.calibration import ScaleCalibration
from app.domain.layer import Layer, LayerKind
from app.domain.stroke import Stroke
from app.domain.units import LengthUnit

DEFAULT_LAYERS: tuple[Layer, ...] = tuple(Layer(kind=kind) for kind in LayerKind)


@dataclass(slots=True)
class DrawingModel:
    """The in-memory project being edited.

    Mutable — unlike the frozen value objects it's built from — because
    the editing canvas (Phase 4) needs to add/remove/move strokes via
    Command objects without rebuilding the whole model on every edit.
    """

    source_image_path: str
    unit: LengthUnit = LengthUnit.MILLIMETRE
    calibration: ScaleCalibration | None = None
    layers: tuple[Layer, ...] = DEFAULT_LAYERS
    strokes: list[Stroke] = field(default_factory=list)

    def strokes_on(self, kind: LayerKind) -> list[Stroke]:
        return [s for s in self.strokes if s.layer == kind]

    def add_stroke(self, stroke: Stroke) -> None:
        self.strokes.append(stroke)

    @property
    def is_calibrated(self) -> bool:
        return self.calibration is not None