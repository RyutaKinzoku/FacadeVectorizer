"""OrthoSnapMergeRegularizer — straightens near-orthogonal strokes and
merges collinear, gap-bridged fragments into continuous lines.

Implements app.application.protocols.GeometryRegularizer. Scope,
deliberately: only straight, 2-point Strokes are touched — everything
Vectorizer currently produces. A Stroke with more than 2 points (no
current producer makes one, but a future stage might) is passed through
unchanged rather than guessed at: there's no single "angle" to snap a
multi-point polyline to, and the Protocol describes this stage as
optional, so "can't usefully simplify it, leave it alone" is a correct
answer here, not a missing feature.

Two passes, in order:

1. Snap — a stroke within ANGLE_SNAP_TOLERANCE_DEGREES of horizontal or
   vertical gets forced exactly level/plumb (average the off-axis
   coordinate across both endpoints). A stroke farther from either axis
   (a genuine diagonal — a roof slope, a cable) is left exactly as drawn.

2. Merge — snapped strokes on the SAME layer, at the SAME ortho position,
   and close enough along their own axis to plausibly be fragments of one
   real edge that EdgeDetector split into dashes, get merged into a
   single Stroke spanning their union. Position grouping uses adjacent-
   gap chain-clustering (sort by position, start a new cluster whenever
   the gap to the previous value exceeds POSITION_BIN_TOLERANCE) rather
   than fixed-width rounding, specifically to avoid the bucket-boundary
   artifact rounding would introduce (two values 0.2 apart landing in
   different buckets purely because they straddle a boundary). Known,
   accepted characteristic of chain-clustering: a long run of values each
   within tolerance of its neighbour can chain into one cluster spanning
   more than POSITION_BIN_TOLERANCE end-to-end. For real edge fragments
   from one detector pass, that span is small in practice; this isn't
   treated as a defect, just documented.

   Within a position cluster, GAP_TOLERANCE decides whether two
   fragments' extents along their own axis are close enough to bridge
   into one continuous line (the "dashed cornice" case) or far enough
   apart to stay separate (two distinct windowsills that merely sit at
   the same height).

Deliberately NOT attempted here: merging diagonal (non-snapped) strokes
by general angle+perpendicular-offset binning. That's a real technique —
it's how the discarded Phase 0 spike approached this — but adds real
complexity for what's mostly roof slopes and cables in practice. A
smaller, well-tested win now beats a bigger, undertested one.

Confidence: when a merge group turns out to be a real merge of 2+
strokes, the output Stroke gets the domain default (1.0) — same
reasoning as Vectorizer's docstring, every input confidence is already
1.0, so there's no real signal to combine into something more
meaningful. When a "group" ends up being exactly one stroke (no actual
merging happened, it just passed through this code path on its way to
possibly being repositioned by cluster averaging), its own original
confidence is preserved rather than being discarded for no reason.
Snapped (non-merged) Strokes likewise keep their original confidence
unchanged, since snapping doesn't add or remove evidence, just nudges
geometry.
Pipeline ordering — load-bearing, not a style note: this stage's
tolerances (ANGLE_SNAP_TOLERANCE_DEGREES aside) are pixel-scale constants.
It MUST run on pixel-space Strokes — i.e. on Vectorizer's output when
Vectorizer was called with calibration=None — never on Strokes a
ScaleCalibration has already scaled into real-world units. Discovered
empirically while validating this against the real uploaded photo: running
it on metre-scale Strokes (calibration applied first) made GAP_TOLERANCE
mean "15 metres" instead of "15 pixels", and the orthogonal subset
collapsed from 123 strokes to 2 — clearly wrong, not a fluke. The correct
pipeline order is Vectorizer(calibration=None) -> regularize -> apply
scale afterwards; there's no scaling step after regularize() yet (nothing
downstream needs one today), so for now this just means: don't calibrate
before you regularize. Whatever eventually builds the real orchestrator
needs to respect this ordering.

"""

from __future__ import annotations

import math

from app.domain.geometry import Point, Polyline
from app.domain.layer import LayerKind
from app.domain.stroke import Stroke

#: A stroke within this many degrees of horizontal or vertical gets
#: snapped exactly level/plumb. Anything farther is left as a diagonal.
ANGLE_SNAP_TOLERANCE_DEGREES = 3.0

#: Two snapped strokes' ortho positions (same units as Stroke geometry)
#: within this distance, via chain-clustering, are candidates for the
#: same real-world edge.
POSITION_BIN_TOLERANCE = 4.0

#: Two same-position strokes whose extents along their own axis are
#: within this gap of touching get merged into one continuous line.
GAP_TOLERANCE = 15.0


class OrthoSnapMergeRegularizer:
    def regularize(self, strokes: list[Stroke]) -> list[Stroke]:
        snapped = [self._snap(stroke) for stroke in strokes]
        return self._merge(snapped)

    # -- pass 1: snap to ortho -------------------------------------------

    def _snap(self, stroke: Stroke) -> Stroke:
        if len(stroke.geometry.points) != 2:
            return stroke  # out of scope -- see module docstring

        start, end = stroke.geometry.points
        orientation = self._orientation(start, end)

        if orientation == "horizontal":
            level = (start.y + end.y) / 2
            start, end = Point(start.x, level), Point(end.x, level)
        elif orientation == "vertical":
            plumb = (start.x + end.x) / 2
            start, end = Point(plumb, start.y), Point(plumb, end.y)
        # else: a genuine diagonal, or a zero-length degenerate stroke --
        # left exactly as drawn either way.

        return Stroke(
            geometry=Polyline(points=(start, end), closed=stroke.geometry.closed),
            layer=stroke.layer,
            confidence=stroke.confidence,
        )

    @staticmethod
    def _orientation(start: Point, end: Point) -> str | None:
        dx, dy = end.x - start.x, end.y - start.y
        if dx == 0 and dy == 0:
            return None  # zero-length -- nothing to snap
        angle = math.degrees(math.atan2(dy, dx)) % 180  # direction only, not sense
        distance_to_horizontal = min(angle, 180 - angle)
        distance_to_vertical = abs(angle - 90)
        if distance_to_horizontal <= ANGLE_SNAP_TOLERANCE_DEGREES:
            return "horizontal"
        if distance_to_vertical <= ANGLE_SNAP_TOLERANCE_DEGREES:
            return "vertical"
        return None

    # -- pass 2: merge collinear fragments --------------------------------

    def _merge(self, strokes: list[Stroke]) -> list[Stroke]:
        passthrough: list[Stroke] = []
        horizontal: dict[LayerKind, list[Stroke]] = {}
        vertical: dict[LayerKind, list[Stroke]] = {}

        for stroke in strokes:
            orientation = self._post_snap_orientation(stroke)
            if orientation == "horizontal":
                horizontal.setdefault(stroke.layer, []).append(stroke)
            elif orientation == "vertical":
                vertical.setdefault(stroke.layer, []).append(stroke)
            else:
                passthrough.append(stroke)

        merged = list(passthrough)
        for layer_strokes in horizontal.values():
            merged.extend(self._merge_same_orientation(layer_strokes, "horizontal"))
        for layer_strokes in vertical.values():
            merged.extend(self._merge_same_orientation(layer_strokes, "vertical"))
        return merged

    @staticmethod
    def _post_snap_orientation(stroke: Stroke) -> str | None:
        if len(stroke.geometry.points) != 2:
            return None
        start, end = stroke.geometry.points
        if start.y == end.y and start.x != end.x:
            return "horizontal"
        if start.x == end.x and start.y != end.y:
            return "vertical"
        return None  # diagonal or zero-length -- not a merge candidate

    def _merge_same_orientation(self, strokes: list[Stroke], orientation: str) -> list[Stroke]:
        """`strokes` here are already confirmed same layer, same
        orientation. Clusters them by their fixed (constant) coordinate
        via adjacent-gap chaining, then merges each cluster's extents
        along its own axis.
        """
        axis_attr = "y" if orientation == "horizontal" else "x"

        def fixed_coordinate(stroke: Stroke) -> float:
            return getattr(stroke.geometry.points[0], axis_attr)

        ordered = sorted(strokes, key=fixed_coordinate)
        position_clusters: list[list[Stroke]] = []
        for stroke in ordered:
            if (
                position_clusters
                and fixed_coordinate(stroke) - fixed_coordinate(position_clusters[-1][-1])
                <= POSITION_BIN_TOLERANCE
            ):
                position_clusters[-1].append(stroke)
            else:
                position_clusters.append([stroke])

        result: list[Stroke] = []
        for cluster in position_clusters:
            result.extend(self._merge_cluster(cluster, orientation, axis_attr))
        return result

    def _merge_cluster(
        self, cluster: list[Stroke], orientation: str, axis_attr: str
    ) -> list[Stroke]:
        average_fixed = sum(
            getattr(stroke.geometry.points[0], axis_attr) for stroke in cluster
        ) / len(cluster)
        layer = cluster[0].layer

        ordered = sorted(cluster, key=lambda stroke: self._extent(stroke, orientation)[0])

        # Parallel lists: groups[i] is which original strokes contributed
        # to the i-th merged interval, bounds[i] is that interval's
        # running [low, high]. Tracking the contributing strokes (not
        # just the numeric bounds) is what lets a single-stroke "merge"
        # (i.e. no real merge at all) keep that stroke's own confidence
        # below, instead of always resetting to the domain default.
        groups: list[list[Stroke]] = []
        bounds: list[list[float]] = []
        for stroke in ordered:
            low, high = self._extent(stroke, orientation)
            if groups and low - bounds[-1][1] <= GAP_TOLERANCE:
                groups[-1].append(stroke)
                bounds[-1][1] = max(bounds[-1][1], high)
            else:
                groups.append([stroke])
                bounds.append([low, high])

        result = []
        for group, (low, high) in zip(groups, bounds, strict=True):
            confidence = group[0].confidence if len(group) == 1 else 1.0
            points = (
                (Point(low, average_fixed), Point(high, average_fixed))
                if orientation == "horizontal"
                else (Point(average_fixed, low), Point(average_fixed, high))
            )
            result.append(
                Stroke(geometry=Polyline(points=points), layer=layer, confidence=confidence)
            )
        return result

    @staticmethod
    def _extent(stroke: Stroke, orientation: str) -> tuple[float, float]:
        start, end = stroke.geometry.points
        if orientation == "horizontal":
            return (min(start.x, end.x), max(start.x, end.x))
        return (min(start.y, end.y), max(start.y, end.y))