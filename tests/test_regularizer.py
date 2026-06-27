"""Tests for OrthoSnapMergeRegularizer.

Snap and merge get tested as separate concerns where possible, plus one
end-to-end test combining both passes -- the actual "fixes the dashed
look" scenario this stage exists for.
"""

from __future__ import annotations

import pytest

from app.application.protocols import GeometryRegularizer
from app.domain.geometry import Point, Polyline
from app.domain.layer import LayerKind
from app.domain.stroke import Stroke
from app.infrastructure.regularization.regularizer import OrthoSnapMergeRegularizer


@pytest.fixture
def regularizer() -> OrthoSnapMergeRegularizer:
    return OrthoSnapMergeRegularizer()


def _stroke(p1: Point, p2: Point, layer: LayerKind = LayerKind.WALLS) -> Stroke:
    return Stroke(geometry=Polyline(points=(p1, p2)), layer=layer)


class TestSnapsNearOrthogonalStrokes:
    def test_near_horizontal_becomes_exactly_level(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        # ~1.9 degrees off horizontal over a 30px run -- within the 3deg tolerance.
        stroke = _stroke(Point(0, 10), Point(30, 11))

        (result,) = regularizer.regularize([stroke])

        start, end = result.geometry.points
        assert start.y == end.y

    def test_near_vertical_becomes_exactly_plumb(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        stroke = _stroke(Point(10, 0), Point(11, 30))

        (result,) = regularizer.regularize([stroke])

        start, end = result.geometry.points
        assert start.x == end.x

    def test_diagonal_far_from_either_axis_is_left_unchanged(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        original = _stroke(Point(0, 0), Point(30, 30))  # a clean 45 degrees

        (result,) = regularizer.regularize([original])

        assert result.geometry.points == original.geometry.points

    def test_multi_point_polyline_is_passed_through_unchanged(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        polyline = Polyline(points=(Point(0, 0), Point(10, 1), Point(20, 0)))
        original = Stroke(geometry=polyline, layer=LayerKind.WALLS)

        (result,) = regularizer.regularize([original])

        assert result is original

    def test_preserves_layer_and_confidence(self, regularizer: OrthoSnapMergeRegularizer) -> None:
        original = Stroke(
            geometry=Polyline(points=(Point(0, 10), Point(30, 11))),
            layer=LayerKind.WINDOWS,
            confidence=0.8,
        )

        (result,) = regularizer.regularize([original])

        assert result.layer == LayerKind.WINDOWS
        assert result.confidence == 0.8

    def test_a_single_stroke_with_no_real_merge_keeps_its_own_confidence(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        # Regression test: a lone stroke still passes through the merge
        # code path (to allow cluster-position averaging), and earlier
        # this unconditionally reset confidence to the domain default
        # even when nothing was actually merged. Two strokes far enough
        # apart that they DON'T merge should each keep their own
        # confidence, not silently lose it.
        strokes = [
            Stroke(
                geometry=Polyline(points=(Point(0, 50), Point(40, 50))),
                layer=LayerKind.WALLS,
                confidence=0.9,
            ),
            Stroke(
                geometry=Polyline(points=(Point(500, 50), Point(540, 50))),
                layer=LayerKind.WALLS,
                confidence=0.4,
            ),
        ]

        result = regularizer.regularize(strokes)

        assert len(result) == 2  # confirmed not merged (gap exceeds tolerance)
        confidences = {round(stroke.confidence, 2) for stroke in result}
        assert confidences == {0.9, 0.4}


class TestMergesCollinearFragments:
    def test_overlapping_horizontal_fragments_merge_into_one(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        fragments = [
            _stroke(Point(0, 50), Point(40, 50)),
            _stroke(Point(35, 50), Point(90, 50)),
        ]

        result = regularizer.regularize(fragments)

        assert len(result) == 1
        start, end = result[0].geometry.points
        assert {start.x, end.x} == {0, 90}

    def test_small_gap_within_tolerance_still_merges(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        # Gap of 10 between the fragments -- inside GAP_TOLERANCE (15).
        fragments = [
            _stroke(Point(0, 50), Point(40, 50)),
            _stroke(Point(50, 50), Point(90, 50)),
        ]

        result = regularizer.regularize(fragments)

        assert len(result) == 1
        start, end = result[0].geometry.points
        assert {start.x, end.x} == {0, 90}

    def test_large_gap_beyond_tolerance_stays_separate(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        # Two distinct windowsills at the same height, far apart in x.
        fragments = [
            _stroke(Point(0, 50), Point(40, 50)),
            _stroke(Point(500, 50), Point(540, 50)),
        ]

        result = regularizer.regularize(fragments)

        assert len(result) == 2

    def test_different_layers_never_merge(self, regularizer: OrthoSnapMergeRegularizer) -> None:
        fragments = [
            _stroke(Point(0, 50), Point(40, 50), layer=LayerKind.WALLS),
            _stroke(Point(35, 50), Point(90, 50), layer=LayerKind.WINDOWS),
        ]

        result = regularizer.regularize(fragments)

        assert len(result) == 2

    def test_horizontal_and_vertical_never_merge_with_each_other(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        fragments = [
            _stroke(Point(0, 50), Point(40, 50)),
            _stroke(Point(20, 0), Point(20, 90)),
        ]

        result = regularizer.regularize(fragments)

        assert len(result) == 2


class TestSnapThenMergeEndToEnd:
    def test_dashed_near_horizontal_fragments_become_one_clean_line(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        # Simulates FastLineDetector noise: several near-horizontal dashes
        # at slightly different y values and small gaps -- the exact
        # "dashed cornice" case this stage exists for.
        fragments = [
            _stroke(Point(0, 100), Point(38, 101)),
            _stroke(Point(45, 99), Point(82, 100)),
            _stroke(Point(88, 100), Point(120, 99)),
        ]

        result = regularizer.regularize(fragments)

        assert len(result) == 1
        start, end = result[0].geometry.points
        assert start.y == end.y  # snapped
        assert {round(start.x), round(end.x)} == {0, 120}  # fully spanned


class TestHandlesEmptyInput:
    def test_returns_empty_list_for_no_strokes(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        assert regularizer.regularize([]) == []


class TestSatisfiesTheProtocol:
    def test_is_a_structural_geometry_regularizer(
        self, regularizer: OrthoSnapMergeRegularizer
    ) -> None:
        assert isinstance(regularizer, GeometryRegularizer)