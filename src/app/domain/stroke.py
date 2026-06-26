"""A single vector entity in the drawing: one shape, assigned to one layer."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.geometry import Polyline
from app.domain.layer import LayerKind


@dataclass(frozen=True, slots=True)
class Stroke:
    """One drawable shape, assigned to exactly one semantic layer.

    `confidence` carries through from whichever pipeline stage produced
    this stroke (an edge detector's response strength, a segmentation
    model's class score, etc.), so the future editing canvas can visually
    flag low-confidence strokes for review — the "ready for CAD cleanup"
    part of the brief, made concrete.
    """

    geometry: Polyline
    layer: LayerKind
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0.")