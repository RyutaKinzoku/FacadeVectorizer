"""Dependency-injection composition root.

This is the ONLY module allowed to import concrete infrastructure classes
and wire them to the Protocols defined in `app.application`. Nothing else
in the codebase should construct an OpenCV/onnxruntime/ezdxf adapter
directly — ask the composition root for one instead.

build_pipeline() now returns a real, working PhotoToCadPipeline (see
app.application.pipeline) wired from the 7 of 9 Protocols that have
concrete adapters today: ImageValidator (PillowImageValidator), Rectifier
(ManualCornerRectifier — manual corners only, no automatic vanishing-point
mode yet), EdgeDetector (CannyFastLineEdgeDetector), Vectorizer
(SingleLayerVectorizer), GeometryRegularizer (OrthoSnapMergeRegularizer),
ScaleCalibrator (SingleMeasurementScaleCalibrator), and DrawingExporter
(PreviewPngExporter + DxfExporter — the one Protocol with two adapters).

Preprocessor (denoise/contrast/undistort, folded informally into
EdgeDetector's own bilateral filter for now) and FacadeSegmenter (Phase 3,
needs a real model) still don't exist, so the pipeline this assembles
doesn't call them — see PhotoToCadPipeline's own docstring. Adding either
later means adding a constructor parameter here and to PhotoToCadPipeline
itself, not restructuring anything.
"""

from __future__ import annotations

from app.application.pipeline import PhotoToCadPipeline
from app.infrastructure.calibration.scale_calibrator import SingleMeasurementScaleCalibrator
from app.infrastructure.export.dxf_exporter import DxfExporter
from app.infrastructure.export.png_exporter import PreviewPngExporter
from app.infrastructure.io.image_validator import PillowImageValidator
from app.infrastructure.regularization.regularizer import OrthoSnapMergeRegularizer
from app.infrastructure.vectorization.vectorizer import SingleLayerVectorizer
from app.infrastructure.vision.edge_detector import CannyFastLineEdgeDetector
from app.infrastructure.vision.rectifier import ManualCornerRectifier


def build_pipeline() -> PhotoToCadPipeline:
    """Assemble the real, working pipeline from concrete infrastructure
    adapters. This is the ONLY function in the codebase that imports
    these concrete classes directly — everywhere else depends on the
    Protocols in app.application.protocols instead (Dependency Inversion).
    """
    return PhotoToCadPipeline(
        image_validator=PillowImageValidator(),
        rectifier=ManualCornerRectifier(),
        edge_detector=CannyFastLineEdgeDetector(),
        vectorizer=SingleLayerVectorizer(),
        scale_calibrator=SingleMeasurementScaleCalibrator(),
        png_exporter=PreviewPngExporter(),
        dxf_exporter=DxfExporter(),
        regularizer=OrthoSnapMergeRegularizer(),
    )