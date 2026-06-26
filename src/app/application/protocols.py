"""Pipeline stage contracts.

Each Protocol below is one stage from docs/architecture.md §3. The future
orchestrator depends only on these — never on a concrete opencv /
onnxruntime / ezdxf class. Concrete implementations live in
app.infrastructure and get wired to these Protocols in app.composition
(Dependency Inversion).

Because these are Protocols (structural typing, PEP 544), a class doesn't
need to inherit from anything to satisfy one — it just needs the matching
method. That's what makes the Strategy pattern free here: a classic-CV
EdgeDetector and a learned-ONNX EdgeDetector are simply two unrelated
classes that both happen to implement `detect`, and the orchestrator never
needs to know which one it was handed.

Pipeline stage 9, "assemble drawing model", deliberately has no Protocol
here: it's plain construction of a DrawingModel from layers + strokes +
calibration, with no swappable strategy and no third-party dependency to
invert away from. The orchestrator does it directly via the domain
dataclasses.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.application.types import ImageArray
from app.domain.calibration import ScaleCalibration
from app.domain.drawing import DrawingModel
from app.domain.geometry import LineSegment, Point
from app.domain.stroke import Stroke
from app.domain.units import LengthUnit


@runtime_checkable
class ImageValidator(Protocol):
    """Stage 1 — reject unsafe or invalid input before anything else runs.

    Implementations enforce file-size and pixel-dimension limits and
    decode defensively per docs/architecture.md §7 (OWASP); they never
    trust EXIF. Raises ValueError (or a subclass) on anything invalid.
    """

    def validate(self, path: str) -> ImageArray: ...


@runtime_checkable
class Preprocessor(Protocol):
    """Stage 2 — denoise / contrast-correct / undistort."""

    def process(self, image: ImageArray) -> ImageArray: ...


@runtime_checkable
class Rectifier(Protocol):
    """Stage 3 — perspective-correct to a fronto-parallel view.

    `manual_corners`, when given, is exactly four points (image pixel
    space) the user dragged onto the wall's actual corners — the fallback
    path for angles automatic vanishing-point detection can't handle.
    """

    def rectify(
        self,
        image: ImageArray,
        manual_corners: tuple[Point, Point, Point, Point] | None = None,
    ) -> ImageArray: ...


@runtime_checkable
class ScaleCalibrator(Protocol):
    """Stage 4 — turn one known real-world dimension into a ScaleCalibration."""

    def calibrate(
        self, pixel_start: Point, pixel_end: Point, known_length: float, unit: LengthUnit
    ) -> ScaleCalibration: ...


@runtime_checkable
class EdgeDetector(Protocol):
    """Stage 5 — extract candidate line segments from the rectified image."""

    def detect(self, image: ImageArray) -> list[LineSegment]: ...


@runtime_checkable
class FacadeSegmenter(Protocol):
    """Stage 6 (Phase 3) — label pixels as wall / window / door / balcony / etc.

    Returns one mask array per semantic class. An implementation that
    returns `{}` is valid — that's the no-op until Phase 3 ships a real
    segmentation model, and lets the rest of the pipeline run unchanged.
    """

    def segment(self, image: ImageArray) -> dict[str, ImageArray]: ...


@runtime_checkable
class Vectorizer(Protocol):
    """Stage 7 — turn raw line segments into layer-assigned Strokes."""

    def vectorize(
        self,
        segments: list[LineSegment],
        segmentation: dict[str, ImageArray] | None,
        calibration: ScaleCalibration | None,
    ) -> list[Stroke]: ...


@runtime_checkable
class GeometryRegularizer(Protocol):
    """Stage 8 (optional) — straighten, snap to ortho, dedupe/join strokes."""

    def regularize(self, strokes: list[Stroke]) -> list[Stroke]: ...


@runtime_checkable
class DrawingExporter(Protocol):
    """Stage 10 — write a DrawingModel to disk.

    Implemented twice — PNG and DXF, see app.infrastructure.export — and
    the orchestrator calls both through this same Protocol.
    """

    def export(self, drawing: DrawingModel, output_path: str) -> None: ...