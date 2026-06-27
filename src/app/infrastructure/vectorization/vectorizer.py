"""SingleLayerVectorizer — turns raw line segments into layer-assigned
Strokes, applying scale calibration when one is available.

Implements app.application.protocols.Vectorizer. With no semantic
segmentation available yet (FacadeSegmenter is still Phase 3, see
docs/architecture.md §3), there's no signal to tell a wall edge from a
window frame from a balcony rail — so every segment goes on the single
catch-all LayerKind.WALLS layer. A non-empty `segmentation` dict raises
NotImplementedError rather than silently being ignored — the same
"fail loud, not silently wrong" choice made for Rectifier's manual-only
mode and EdgeDetector's classic-only strategy.

Deliberately NOT this stage's job, per docs/architecture.md §3 (stage 7
vs stage 8): merging near-duplicate segments, snapping to orthogonal, and
deduping/joining. That's GeometryRegularizer's job — a separate, optional
stage. This Vectorizer is a pure 1:1 mapping: one Stroke per LineSegment.

Confidence: every Stroke keeps the domain default (1.0). There's no real
per-segment score to report yet — EdgeDetector's LineSegment carries no
score, and inventing a number wouldn't be a real confidence signal, just
a fake one. A future stage with an actual score (a segmentation model's
class probability, or a regularizer's merge quality) should set it for
real, not this one.

Scaling: delegates to ScaleCalibration.to_real_point rather than
re-deriving "divide by pixels_per_unit" here — see that method's
docstring for why it lives in the domain object instead of this adapter
(the orchestrator needs the exact same operation applied to already-
regularized Strokes, not just at this call site).
"""

from __future__ import annotations

from app.application.types import ImageArray
from app.domain.calibration import ScaleCalibration
from app.domain.geometry import LineSegment, Polyline
from app.domain.layer import LayerKind
from app.domain.stroke import Stroke


class SingleLayerVectorizer:
    def vectorize(
        self,
        segments: list[LineSegment],
        segmentation: dict[str, ImageArray] | None,
        calibration: ScaleCalibration | None,
    ) -> list[Stroke]:
        if segmentation:  # None and {} both mean "no segmentation available"
            raise NotImplementedError(
                "Segmentation-aware layer assignment isn't implemented yet "
                "(see docs/architecture.md, Phase 3) — pass segmentation=None "
                "or an empty dict until a real FacadeSegmenter exists."
            )

        return [
            Stroke(geometry=self._to_polyline(segment, calibration), layer=LayerKind.WALLS)
            for segment in segments
        ]

    @staticmethod
    def _to_polyline(segment: LineSegment, calibration: ScaleCalibration | None) -> Polyline:
        start, end = segment.start, segment.end
        if calibration is not None:
            start = calibration.to_real_point(start)
            end = calibration.to_real_point(end)
        return Polyline(points=(start, end))