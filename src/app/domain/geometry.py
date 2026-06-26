"""Pure geometry value objects — no image, no CAD library, no UI dependency.

These describe shapes in a single, consistent 2D coordinate space: the
rectified drawing plane, in pixels until a ScaleCalibration is applied (see
domain.calibration), in real-world units afterwards. Everything here is an
immutable dataclass; nothing here imports numpy, cv2, PySide6, or ezdxf.

Curved elements (arcs) are deliberately out of scope for this commit — the
MVP pipeline only needs straight-line geometry. Add an Arc value object
here when a pipeline stage actually needs one, not before.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True, slots=True)
class Point:
    """A single 2D point in drawing-space units."""

    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True, slots=True)
class LineSegment:
    """A straight segment between two points."""

    start: Point
    end: Point

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)


@dataclass(frozen=True, slots=True)
class Polyline:
    """An ordered sequence of points — the shape a Stroke wraps.

    Open by default. A closed polyline (e.g. a window outline) sets
    `closed=True`, which exporters interpret as an implicit segment back
    from the last point to the first.
    """

    points: tuple[Point, ...]
    closed: bool = False

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("A Polyline needs at least two points.")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned bounding box — used for canvas framing and hit-testing."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @classmethod
    def from_points(cls, points: tuple[Point, ...]) -> BoundingBox:
        if not points:
            raise ValueError("Cannot compute a bounding box of zero points.")
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        return cls(min(xs), min(ys), max(xs), max(ys))

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y